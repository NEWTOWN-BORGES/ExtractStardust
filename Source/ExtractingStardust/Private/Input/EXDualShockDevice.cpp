#include "Input/EXDualShockDevice.h"

#include "GenericPlatform/GenericApplicationMessageHandler.h"
#include "GenericPlatform/GenericPlatformInputDeviceMapper.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

#if PLATFORM_WINDOWS
#include "Windows/WindowsHWrapper.h"
#include "Windows/AllowWindowsPlatformTypes.h"
#include <SetupAPI.h>
#include <hidsdi.h>
#include "Windows/HideWindowsPlatformTypes.h"
#endif

namespace
{
	namespace PadBit
	{
		constexpr uint32 Cross = 1u << 0;
		constexpr uint32 Circle = 1u << 1;
		constexpr uint32 Square = 1u << 2;
		constexpr uint32 Triangle = 1u << 3;
		constexpr uint32 L1 = 1u << 4;
		constexpr uint32 R1 = 1u << 5;
		constexpr uint32 Share = 1u << 6;
		constexpr uint32 Options = 1u << 7;
		constexpr uint32 L3 = 1u << 8;
		constexpr uint32 R3 = 1u << 9;
		constexpr uint32 Up = 1u << 10;
		constexpr uint32 Down = 1u << 11;
		constexpr uint32 Left = 1u << 12;
		constexpr uint32 Right = 1u << 13;
		constexpr uint32 L2 = 1u << 14;
		constexpr uint32 R2 = 1u << 15;
	}

	constexpr uint16 SonyVendorId = 0x054C;
	constexpr float TriggerPressThreshold = 0.3f;

	float StickAxis(uint8 Value, bool bInvert)
	{
		const float Axis = FMath::Clamp((static_cast<float>(Value) - 127.5f) / 127.5f, -1.0f, 1.0f);
		return bInvert ? -Axis : Axis;
	}
}

struct FEXDualShockDevice::FHidConnection
{
#if PLATFORM_WINDOWS
	HANDLE Handle = INVALID_HANDLE_VALUE;
	OVERLAPPED Overlapped = {};
	TArray<uint8> Buffer;
	bool bReadPending = false;
	bool bDualSense = false;
	bool bBluetooth = false;
#endif
};

FEXDualShockDevice::FEXDualShockDevice(const TSharedRef<FGenericApplicationMessageHandler>& InMessageHandler)
	: MessageHandler(InMessageHandler)
	, Connection(MakeUnique<FHidConnection>())
{
	bLogDiagnostics = FParse::Param(FCommandLine::Get(), TEXT("EXFlightTest")) || FParse::Param(FCommandLine::Get(), TEXT("EXPadLog"));
	TryConnect();
}

FEXDualShockDevice::~FEXDualShockDevice()
{
	Disconnect();
}

void FEXDualShockDevice::SetMessageHandler(const TSharedRef<FGenericApplicationMessageHandler>& InMessageHandler)
{
	MessageHandler = InMessageHandler;
}

bool FEXDualShockDevice::IsGamepadAttached() const
{
#if PLATFORM_WINDOWS
	return Connection->Handle != INVALID_HANDLE_VALUE;
#else
	return false;
#endif
}

void FEXDualShockDevice::TryConnect()
{
#if PLATFORM_WINDOWS
	GUID HidGuid;
	HidD_GetHidGuid(&HidGuid);
	HDEVINFO DeviceInfo = SetupDiGetClassDevsW(&HidGuid, nullptr, nullptr, DIGCF_PRESENT | DIGCF_DEVICEINTERFACE);
	if (DeviceInfo == INVALID_HANDLE_VALUE)
	{
		return;
	}
	SP_DEVICE_INTERFACE_DATA InterfaceData;
	InterfaceData.cbSize = sizeof(InterfaceData);
	for (DWORD Index = 0; SetupDiEnumDeviceInterfaces(DeviceInfo, nullptr, &HidGuid, Index, &InterfaceData); ++Index)
	{
		DWORD RequiredSize = 0;
		SetupDiGetDeviceInterfaceDetailW(DeviceInfo, &InterfaceData, nullptr, 0, &RequiredSize, nullptr);
		if (RequiredSize == 0)
		{
			continue;
		}
		TArray<uint8> DetailStorage;
		DetailStorage.SetNumZeroed(RequiredSize);
		SP_DEVICE_INTERFACE_DETAIL_DATA_W* Detail = reinterpret_cast<SP_DEVICE_INTERFACE_DETAIL_DATA_W*>(DetailStorage.GetData());
		Detail->cbSize = sizeof(SP_DEVICE_INTERFACE_DETAIL_DATA_W);
		if (!SetupDiGetDeviceInterfaceDetailW(DeviceInfo, &InterfaceData, Detail, RequiredSize, nullptr, nullptr))
		{
			continue;
		}

		// Identify the device without read access first: only Sony pads exposing the gamepad collection qualify.
		HANDLE Probe = CreateFileW(Detail->DevicePath, 0, FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_EXISTING, 0, nullptr);
		if (Probe == INVALID_HANDLE_VALUE)
		{
			continue;
		}
		HIDD_ATTRIBUTES Attributes = {};
		Attributes.Size = sizeof(Attributes);
		HIDP_CAPS Caps = {};
		const bool bSony = HidD_GetAttributes(Probe, &Attributes) != 0 && Attributes.VendorID == SonyVendorId;
		PHIDP_PREPARSED_DATA Preparsed = nullptr;
		if (bSony && HidD_GetPreparsedData(Probe, &Preparsed) != 0)
		{
			HidP_GetCaps(Preparsed, &Caps);
			HidD_FreePreparsedData(Preparsed);
		}
		CloseHandle(Probe);

		const uint16 ProductId = Attributes.ProductID;
		const bool bDualShock4 = ProductId == 0x05C4 || ProductId == 0x09CC || ProductId == 0x0BA0;
		const bool bDualSense = ProductId == 0x0CE6 || ProductId == 0x0DF2;
		if (!bSony || !(bDualShock4 || bDualSense) || Caps.UsagePage != 0x01 || Caps.Usage != 0x05 || Caps.InputReportByteLength == 0)
		{
			continue;
		}

		HANDLE Handle = CreateFileW(Detail->DevicePath, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_EXISTING, FILE_FLAG_OVERLAPPED, nullptr);
		if (Handle == INVALID_HANDLE_VALUE)
		{
			Handle = CreateFileW(Detail->DevicePath, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_EXISTING, FILE_FLAG_OVERLAPPED, nullptr);
		}
		if (Handle == INVALID_HANDLE_VALUE)
		{
			continue;
		}
		// A short queue keeps the newest report close at hand.
		HidD_SetNumInputBuffers(Handle, 4);
		Connection->Handle = Handle;
		Connection->Overlapped = {};
		Connection->Overlapped.hEvent = CreateEventW(nullptr, 1, 0, nullptr);
		Connection->Buffer.SetNumZeroed(Caps.InputReportByteLength);
		Connection->bReadPending = false;
		Connection->bDualSense = bDualSense;
		Connection->bBluetooth = Caps.InputReportByteLength != 64;
		UE_LOG(LogTemp, Display, TEXT("EXPAD connected: Sony %s (PID 0x%04X) over %s, report %d bytes."),
			bDualSense ? TEXT("DualSense") : TEXT("DualShock 4"), ProductId, Connection->bBluetooth ? TEXT("Bluetooth") : TEXT("USB"),
			static_cast<int32>(Caps.InputReportByteLength));
		break;
	}
	SetupDiDestroyDeviceInfoList(DeviceInfo);
#endif
}

void FEXDualShockDevice::Disconnect()
{
#if PLATFORM_WINDOWS
	if (Connection->Handle != INVALID_HANDLE_VALUE)
	{
		if (Connection->bReadPending)
		{
			CancelIoEx(Connection->Handle, &Connection->Overlapped);
			DWORD Ignored = 0;
			GetOverlappedResult(Connection->Handle, &Connection->Overlapped, &Ignored, 1);
		}
		CloseHandle(Connection->Handle);
		Connection->Handle = INVALID_HANDLE_VALUE;
	}
	if (Connection->Overlapped.hEvent)
	{
		CloseHandle(Connection->Overlapped.hEvent);
		Connection->Overlapped.hEvent = nullptr;
	}
	Connection->bReadPending = false;
#endif
	// Release everything that was held so no input stays stuck after unplugging.
	State = FPadState();
}

void FEXDualShockDevice::Tick(float DeltaTime)
{
#if PLATFORM_WINDOWS
	if (Connection->Handle == INVALID_HANDLE_VALUE)
	{
		ReconnectTimer -= DeltaTime;
		if (ReconnectTimer <= 0.0f)
		{
			ReconnectTimer = 2.0f;
			TryConnect();
		}
		return;
	}
	// Drain every report that arrived since the last frame so the input never lags behind the pad.
	for (int32 Guard = 0; Guard < 64; ++Guard)
	{
		DWORD BytesRead = 0;
		if (!Connection->bReadPending)
		{
			ResetEvent(Connection->Overlapped.hEvent);
			if (ReadFile(Connection->Handle, Connection->Buffer.GetData(), Connection->Buffer.Num(), &BytesRead, &Connection->Overlapped) != 0)
			{
				ParseReport(Connection->Buffer.GetData(), static_cast<int32>(BytesRead));
				continue;
			}
			if (GetLastError() != ERROR_IO_PENDING)
			{
				UE_LOG(LogTemp, Display, TEXT("EXPAD disconnected."));
				Disconnect();
				return;
			}
			Connection->bReadPending = true;
		}
		if (GetOverlappedResult(Connection->Handle, &Connection->Overlapped, &BytesRead, 0) == 0)
		{
			if (GetLastError() == ERROR_IO_INCOMPLETE)
			{
				break;
			}
			UE_LOG(LogTemp, Display, TEXT("EXPAD disconnected."));
			Disconnect();
			return;
		}
		Connection->bReadPending = false;
		ParseReport(Connection->Buffer.GetData(), static_cast<int32>(BytesRead));
	}
#endif
	if (bLogDiagnostics)
	{
		DiagnosticTimer -= DeltaTime;
		if (DiagnosticTimer <= 0.0f)
		{
			DiagnosticTimer = 2.0f;
			UE_LOG(LogTemp, Display, TEXT("EXPAD reports=%d LX=%.2f LY=%.2f RX=%.2f RY=%.2f L2=%.2f R2=%.2f buttons=0x%04X"), ReportCount,
				State.Axes[0], State.Axes[1], State.Axes[2], State.Axes[3], State.Axes[4], State.Axes[5], State.Buttons);
		}
	}
}

void FEXDualShockDevice::ParseReport(const uint8* Report, int32 Length)
{
#if PLATFORM_WINDOWS
	if (Length < 10)
	{
		return;
	}
	// Report layouts: DualShock 4 USB/Bluetooth-simple 0x01, DualShock 4 Bluetooth 0x11 (+2 bytes),
	// DualSense USB 0x01, DualSense Bluetooth-simple 0x01 (DualShock 4 layout), DualSense Bluetooth 0x31 (+1 byte).
	int32 Offset = -1;
	bool bDualSenseLayout = false;
	if (!Connection->bDualSense)
	{
		Offset = Report[0] == 0x01 ? 1 : Report[0] == 0x11 ? 3 : -1;
	}
	else if (Report[0] == 0x01)
	{
		Offset = 1;
		bDualSenseLayout = !Connection->bBluetooth;
	}
	else if (Report[0] == 0x31)
	{
		Offset = 2;
		bDualSenseLayout = true;
	}
	if (Offset < 0 || Offset + 10 > Length)
	{
		return;
	}
	const uint8* Data = Report + Offset;
	const uint8 Face = bDualSenseLayout ? Data[7] : Data[4];
	const uint8 Shoulders = bDualSenseLayout ? Data[8] : Data[5];
	const uint8 LeftTrigger = bDualSenseLayout ? Data[4] : Data[7];
	const uint8 RightTrigger = bDualSenseLayout ? Data[5] : Data[8];

	State.Axes[0] = StickAxis(Data[0], false);
	State.Axes[1] = StickAxis(Data[1], true);
	State.Axes[2] = StickAxis(Data[2], false);
	State.Axes[3] = StickAxis(Data[3], true);
	State.Axes[4] = LeftTrigger / 255.0f;
	State.Axes[5] = RightTrigger / 255.0f;

	uint32 Buttons = 0;
	const uint8 Hat = Face & 0x0F;
	if (Hat == 7 || Hat == 0 || Hat == 1) { Buttons |= PadBit::Up; }
	if (Hat >= 1 && Hat <= 3) { Buttons |= PadBit::Right; }
	if (Hat >= 3 && Hat <= 5) { Buttons |= PadBit::Down; }
	if (Hat >= 5 && Hat <= 7) { Buttons |= PadBit::Left; }
	if (Face & 0x10) { Buttons |= PadBit::Square; }
	if (Face & 0x20) { Buttons |= PadBit::Cross; }
	if (Face & 0x40) { Buttons |= PadBit::Circle; }
	if (Face & 0x80) { Buttons |= PadBit::Triangle; }
	if (Shoulders & 0x01) { Buttons |= PadBit::L1; }
	if (Shoulders & 0x02) { Buttons |= PadBit::R1; }
	if (Shoulders & 0x10) { Buttons |= PadBit::Share; }
	if (Shoulders & 0x20) { Buttons |= PadBit::Options; }
	if (Shoulders & 0x40) { Buttons |= PadBit::L3; }
	if (Shoulders & 0x80) { Buttons |= PadBit::R3; }
	if (State.Axes[4] > TriggerPressThreshold) { Buttons |= PadBit::L2; }
	if (State.Axes[5] > TriggerPressThreshold) { Buttons |= PadBit::R2; }
	State.Buttons = Buttons;
	++ReportCount;
#endif
}

void FEXDualShockDevice::SendControllerEvents()
{
	IPlatformInputDeviceMapper& Mapper = IPlatformInputDeviceMapper::Get();
	const FPlatformUserId UserId = Mapper.GetPrimaryPlatformUser();
	const FInputDeviceId DeviceId = Mapper.GetDefaultInputDevice();

	// Analog values are sent while the pad is attached, plus one final zero after it goes away.
	if (IsGamepadAttached() || bAnalogActive)
	{
		const FGamepadKeyNames::Type AxisKeys[6] = { FGamepadKeyNames::LeftAnalogX, FGamepadKeyNames::LeftAnalogY, FGamepadKeyNames::RightAnalogX,
			FGamepadKeyNames::RightAnalogY, FGamepadKeyNames::LeftTriggerAnalog, FGamepadKeyNames::RightTriggerAnalog };
		for (int32 Index = 0; Index < 6; ++Index)
		{
			MessageHandler->OnControllerAnalog(AxisKeys[Index], UserId, DeviceId, State.Axes[Index]);
		}
		bAnalogActive = IsGamepadAttached();
	}

	struct FButtonKey
	{
		uint32 Bit;
		FGamepadKeyNames::Type Key;
	};
	const FButtonKey ButtonKeys[] = {
		{ PadBit::Cross, FGamepadKeyNames::FaceButtonBottom }, { PadBit::Circle, FGamepadKeyNames::FaceButtonRight },
		{ PadBit::Square, FGamepadKeyNames::FaceButtonLeft }, { PadBit::Triangle, FGamepadKeyNames::FaceButtonTop },
		{ PadBit::L1, FGamepadKeyNames::LeftShoulder }, { PadBit::R1, FGamepadKeyNames::RightShoulder },
		{ PadBit::Share, FGamepadKeyNames::SpecialLeft }, { PadBit::Options, FGamepadKeyNames::SpecialRight },
		{ PadBit::L3, FGamepadKeyNames::LeftThumb }, { PadBit::R3, FGamepadKeyNames::RightThumb },
		{ PadBit::Up, FGamepadKeyNames::DPadUp }, { PadBit::Down, FGamepadKeyNames::DPadDown },
		{ PadBit::Left, FGamepadKeyNames::DPadLeft }, { PadBit::Right, FGamepadKeyNames::DPadRight },
		{ PadBit::L2, FGamepadKeyNames::LeftTriggerThreshold }, { PadBit::R2, FGamepadKeyNames::RightTriggerThreshold } };
	for (const FButtonKey& Button : ButtonKeys)
	{
		const bool bDown = (State.Buttons & Button.Bit) != 0;
		const bool bWasDown = (SentButtons & Button.Bit) != 0;
		if (bDown && !bWasDown)
		{
			MessageHandler->OnControllerButtonPressed(Button.Key, UserId, DeviceId, false);
		}
		else if (!bDown && bWasDown)
		{
			MessageHandler->OnControllerButtonReleased(Button.Key, UserId, DeviceId, false);
		}
	}
	SentButtons = State.Buttons;
}
