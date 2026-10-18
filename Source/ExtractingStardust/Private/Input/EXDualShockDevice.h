#pragma once

#include "CoreMinimal.h"
#include "IInputDevice.h"

class FGenericApplicationMessageHandler;

/**
 * Reads Sony DualShock 4 and DualSense pads over Windows HID (USB or Bluetooth) and feeds them to Unreal as a
 * standard gamepad, so they drive the same Gamepad_* keys as an Xbox pad. Windows does not expose these pads
 * through XInput, and the engine's own DualShock plugin needs Sony's SDK.
 */
class FEXDualShockDevice : public IInputDevice
{
public:
	explicit FEXDualShockDevice(const TSharedRef<FGenericApplicationMessageHandler>& InMessageHandler);
	virtual ~FEXDualShockDevice() override;

	virtual void Tick(float DeltaTime) override;
	virtual void SendControllerEvents() override;
	virtual void SetMessageHandler(const TSharedRef<FGenericApplicationMessageHandler>& InMessageHandler) override;
	virtual bool Exec(UWorld* InWorld, const TCHAR* Cmd, FOutputDevice& Ar) override { return false; }
	virtual void SetChannelValue(int32 ControllerId, FForceFeedbackChannelType ChannelType, float Value) override {}
	virtual void SetChannelValues(int32 ControllerId, const FForceFeedbackValues& Values) override {}
	virtual bool IsGamepadAttached() const override;

private:
	struct FHidConnection;

	struct FPadState
	{
		/** LX, LY, RX, RY in -1..1 (up is positive), then L2 and R2 in 0..1. */
		float Axes[6] = { 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f };
		uint32 Buttons = 0;
	};

	void TryConnect();
	void Disconnect();
	void ParseReport(const uint8* Report, int32 Length);

	TSharedRef<FGenericApplicationMessageHandler> MessageHandler;
	TUniquePtr<FHidConnection> Connection;
	FPadState State;
	uint32 SentButtons = 0;
	bool bAnalogActive = false;
	float ReconnectTimer = 0.0f;
	int32 ReportCount = 0;
	float DiagnosticTimer = 0.0f;
	bool bLogDiagnostics = false;
};
