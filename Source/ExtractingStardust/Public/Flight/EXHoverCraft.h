#pragma once

#include "CoreMinimal.h"
#include "Game/EXMeta.h"
#include "GameFramework/Pawn.h"
#include "EXHoverCraft.generated.h"

class UBoxComponent;
class UCameraComponent;
class UEXCraftFx;
class UEXCraftAudio;
struct FEXCraftAudioInput;
class UEXProfileSave;
class UEXHangarModel;
class AEXHangarStage;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class USceneComponent;
class UStaticMesh;
class UStaticMeshComponent;

/**
 * Free-flying hover craft used to tune the handling feel. It is not attached to any track: it hovers over
 * whatever surface is below it and falls under gravity when there is none.
 * Handling and chase camera follow the previous game's controller, which the player had tuned.
 * Units: metres and seconds; angular rates in rad/s unless the name says Deg.
 */
UCLASS()
class EXTRACTINGSTARDUST_API AEXHoverCraft : public APawn
{
	GENERATED_BODY()

public:
	AEXHoverCraft();

	virtual void Tick(float DeltaSeconds) override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

	UFUNCTION(BlueprintCallable, Category = "Flight")
	void ResetToStart();

	UFUNCTION(BlueprintCallable, Category = "Flight")
	void SelectShip(int32 Index);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Speed") float MaxSpeedMps = 118.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Speed") float BoostTopMul = 1.16f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Speed") float AccelerationMps2 = 36.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Speed") float BoostAccelerationMps2 = 34.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Speed") float BrakeMps2 = 44.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Speed") float CoastDecelMps2 = 6.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Speed") float OverspeedBleed = 0.6f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Speed") float AeroDrag = 0.00012f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Speed") float ReverseMaxSpeedMps = 15.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Speed") float AirThrust = 0.3f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Speed") float NitroSeconds = 3.4f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Speed") float NitroRegen = 0.20f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Speed") float NitroDriftRegen = 0.30f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Speed") float NitroAirRegen = 0.15f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Steering") float TurnRateLow = 2.4f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Steering") float TurnRateHigh = 1.05f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Steering") float SteerResponse = 10.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Steering") float AirTurnMul = 0.35f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Steering") float BrakeTurnMul = 1.35f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Grip") float GripRedirect = 5.5f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Grip") float GripLateralMax = 85.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Grip") float GripFriction = 1.2f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Grip") float GripBase = 0.10f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Grip") float GripSpeedRef = 125.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Grip") float GripCap = 0.55f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Grip") float BrakeGripMul = 1.25f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Drift") float DriftRedirect = 2.2f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Drift") float DriftLateralMax = 62.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Drift") float DriftTurnMul = 1.6f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Drift") float DriftDecel = 3.5f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Drift") float DriftKick = 0.45f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Drift") float DriftMaxSlipDeg = 32.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Drift") float DriftRecoverTime = 0.35f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Drift") float DriftBoost = 10.0f;

	/** Soft, long spring (natural frequency ~1 Hz) so landings settle instead of bouncing. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Hover") float HoverHeightM = 1.5f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Hover") float HoverStiffness = 40.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Hover") float HoverDamping = 1.25f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Hover") float GravityMps2 = 22.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Hover") float SlopeGravityScale = 0.6f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Hover") float SurfaceAlignDegPerSec = 160.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Hover") float AirLevelDegPerSec = 45.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Hover") float WallBounce = 0.3f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Hover") float WallScrapeLoss = 0.2f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Visual") float BankMaxDeg = 38.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Visual") float NoseLeadMaxDeg = 8.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Visual") float PitchFromAccel = 0.16f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Visual") float VisualResponse = 9.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float CamDistanceM = 5.8f;
	/** Negative: the camera closes in at top speed. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float CamDistanceAtSpeedM = -1.6f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float CamHeightM = 1.45f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float CamHeightAtSpeedM = -0.55f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float CamLookAheadM = 22.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float CamLookHeightM = 0.55f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float CamUpFollow = 0.75f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float CamRollFollow = 0.72f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float CamOffsetStiffness = 5.5f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float CamUpSmoothing = 5.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float CamHeadingSmoothing = 6.5f;
	/** Vertical field of view in degrees, as in the previous game; converted to Unreal's horizontal FOV. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float FovMinV = 68.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float FovMaxV = 112.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float FovBoostV = 14.0f;
	/** Speeds (km/h) between which the vertigo effect (wider FOV, shake) builds up. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float VertigoKmhMin = 180.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float VertigoKmhMax = 450.0f;
	/** Light vibration near top speed, in degrees (the player preferred this to the old noise shake). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float TopSpeedShakeDeg = 0.55f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float ShakeScale = 1.0f;
	/** Share of the craft's visual bank that the camera follows. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float CameraBankFollow = 0.82f;
	/** Camera looks into the apex and hangs slightly outside the turn. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float CamLookIntoTurnDeg = 12.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float CamOutboardM = 1.35f;
	/** Peak camera jolt on a hard landing or wall hit, in degrees. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float LandingShakeDeg = 2.2f;
	/** How far the right stick orbits the camera around the craft. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Camera") float LookYawMaxDeg = 120.0f;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components") TObjectPtr<UBoxComponent> Collision;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components") TObjectPtr<USceneComponent> VisualPivot;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components") TObjectPtr<UStaticMeshComponent> ShipMesh;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components") TObjectPtr<UCameraComponent> Camera;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components") TObjectPtr<UEXCraftFx> Fx;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components") TObjectPtr<UEXCraftAudio> Audio;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Ships") TArray<TObjectPtr<UStaticMesh>> ShipMeshes;
	/** Yaw that turns the imported test models (long axis on Y) to face +X. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Flight|Ships") float ModelYawOffsetDeg = -90.0f;

	/** For the HUD: the map's race line (metres, 5 m apart), the nearest point of it, the nose and the velocity. */
	const TArray<FVector2D>& GetMapRoute() const { return MapRoute; }

	// ---- Race rules (Docs/MODOS_DE_JOGO.md), switched on by AEXRaceDirector; off in free flight and the tests.
	/** Lives by ship (plus the hull of the modules), damage from hard wall hits and hard landings, fuel and heat. */
	void SetRaceRules();
	/** Makes this craft a bot that drives itself along the race line (skill 0.8-1.0, lane offset from the line in m). */
	void SetBot(int32 InShipIndex, float InSkill, float InLaneM);
	/** Holds the craft on the grid (countdown, after the finish). */
	void SetRaceHold(bool bHold) { bRaceHold = bHold; }
	/** Showroom: the craft stands on the turntable of the workshop (AEXHangarStage) under a slow orbit camera, with the
	 *  menu drawn over it. EnterHangar opens the hangar's tabs (UEXHangarModel): ship, modules, consumables, shop and
	 *  vault, paid with the STARDUST of the profile. */
	void EnterShowroom();
	/** Back to where the craft stood before the showroom (the start of the race line). */
	void ExitShowroom();
	bool IsInShowroom() const { return bInShowroom; }
	void EnterHangar();
	/** From the hangar back to the menu: the craft stays on the turntable and the lights go down. */
	void LeaveHangar();
	bool IsInHangar() const { return bInHangar; }
	/** The ships this craft can be (the meshes found), for the hangar roster. */
	int32 GetShipCount() const { return ShipMeshes.Num(); }
	FString GetShipNameAt(int32 Index) const;
	/** Top speed before the ship's multiplier, m/s. */
	float GetBaseTopSpeedMps() const { return BaseMaxSpeedMps > 0.0f ? BaseMaxSpeedMps : MaxSpeedMps; }
	/** Race stats of a ship by name: lives, top speed against the base, speed into a wall that costs a life (m/s). */
	static void GetShipRaceStats(const FString& Name, int32& OutLives, float& OutSpeedMul, float& OutWallHitMps);
	/** The pilot's saved profile (wallet, modules, consumables), loaded on first use; the player's craft only. */
	UEXProfileSave* EnsureProfile();
	UEXProfileSave* GetProfile() const { return Profile; }
	UEXHangarModel* GetHangarModel() const { return HangarModel; }
	/** From the hangar's ship tab: start the expedition. */
	void LaunchFromHangar() { HangarLaunch(); }

	// ---- Modules and consumables (Docs/MODULOS.md)
	/** The modules this craft flies with, by EEXFamily (an empty item is the stock part): the race stats, the pieces on
	 *  the hull, the engine's flame and the nitro's colour. */
	void SetModules(const TArray<FEXItem>& InModules);
	const TArray<FEXItem>& GetModules() const { return Modules; }
	/** Final stats of the ship and its modules (EEXStat order). */
	int32 GetStat(EEXStat Stat) const { return ResolvedStats[FMath::Clamp(static_cast<int32>(Stat), 0, EXMeta::StatCount - 1)]; }
	/** The four quick slots carried into the race: keys 1-4, d-pad up, down, left and right. */
	void SetQuickSlots(const TArray<FEXQuickSlot>& InSlots);
	const TArray<FEXQuickSlot>& GetQuickSlots() const { return QuickSlots; }
	/** Fuel and heat, 0-100. Without fuel the craft has half its top speed; at 100 heat it overheats (no nitro until 40). */
	float GetFuel() const { return Fuel; }
	float GetHeat() const { return Heat; }
	bool IsOverheated() const { return bOverheated; }
	float GetNitro() const { return Nitro; }
	/** A repair under way (foam or nanogel): 0-1 done, -1 when none. */
	float GetRepairProgress() const { return RepairTotal > 0.0f ? 1.0f - RepairLeft / RepairTotal : -1.0f; }
	float GetStabilizerLeft() const { return StabLeft; }
	/** The last quick slot used and when (world time), for the HUD; -1 if none. */
	int32 GetLastQuickSlot() const { return LastQuickSlot; }
	float GetLastQuickTime() const { return LastQuickTime; }
	/** Hangar preview: the craft wears this build. Looking at a slot inside the hull (engine, propulsion, reactor,
	 *  utility) the bodywork goes, the skeleton shows and the engine runs with its flame. */
	void PreviewModules(const TArray<FEXItem>& InModules, EEXFamily Focus);
	/** Where a module sits on the ship, in the world (the hangar pins its notes there): the piece on the hull, else a
	 *  point of the hull for the parts inside it (engine and propulsion at the back, the reactor in the middle). */
	bool GetModuleAnchor(EEXFamily Family, FVector& OutWorld) const;
	/** No more ship changes once the race is on. */
	void LockShip() { bShipLocked = true; }
	/** Puts the craft at a place and heading, at rest (grid slots, respawns). */
	void PlaceAt(const FVector& Location, float YawDeg);
	void Eliminate();
	bool IsBot() const { return bBot; }
	bool IsEliminated() const { return bEliminated; }
	int32 GetLives() const { return Lives; }
	int32 GetMaxLives() const { return MaxLives; }
	/** World time of the last life lost (the HUD flashes it), -1 if none. */
	float GetLastHitTime() const { return LastHitTime; }
	FString GetShipName() const;
	int32 GetShipIndex() const { return ShipIndex; }
	float GetSpeedKmh() const { return FMath::Abs(ForwardSpeedMps) * 3.6f; }
	/** Furthest point reached along the race line, in metres (never jumps more than 600 m at once). */
	float GetRaceProgressM() const { return RaceProgressM; }
	int32 GetRouteIndex() const { return RouteIndex; }
	FVector GetHeading() const { return Heading; }
	FVector GetFlightVelocity() const { return VelocityCmps; }
	float GetThrottle() const { return ThrottleInput; }
	bool IsBoosting() const { return bBoosting; }

protected:
	virtual void BeginPlay() override;

private:
	void StepFlight(float Dt);
	void MoveWithCollision(float Dt);
	void UpdateVisuals(float Dt);
	void UpdateCamera(float Dt);
	void ShowTelemetry() const;
	void RunFlightTest(float Dt);
	void RunDesertTest(float Dt);
	void RunTour(float Dt);

	void InputThrottle(float Value) { ThrottleInput = FMath::Clamp(Value, 0.0f, 1.0f); }
	void InputBrake(float Value) { BrakeInput = FMath::Clamp(Value, 0.0f, 1.0f); }
	void InputSteer(float Value) { SteerInput = FMath::Clamp(Value, -1.0f, 1.0f); }
	void BoostPressed() { bBoostHeld = true; }
	void BoostReleased() { bBoostHeld = false; }
	void DriftPressed() { bDriftHeld = true; }
	void DriftReleased() { bDriftHeld = false; }
	void InputLookYaw(float Value) { LookYawInput = FMath::Clamp(Value, -1.0f, 1.0f); }
	void LookBackPressed() { bLookBack = true; }
	void LookBackReleased() { bLookBack = false; }
	void QuitPressed();
	void NextShip() { SelectShip(ShipIndex + 1); }
	void PrevShip() { SelectShip(ShipIndex - 1); }
	void Ship1() { SelectShip(0); }
	void Ship2() { SelectShip(1); }
	void Ship3() { SelectShip(2); }
	void Ship4() { SelectShip(3); }
	void Ship5() { SelectShip(4); }
	void CycleCamera() { CameraMode = (CameraMode + 1) % 4; bCamInitialized = false; }
	void UseQuick(int32 Slot);
	void Quick1() { UseQuick(0); }
	void Quick2() { UseQuick(1); }
	void Quick3() { UseQuick(2); }
	void Quick4() { UseQuick(3); }
	void MenuUp() { SendMenu(-1); }
	void MenuDown() { SendMenu(1); }
	void MenuConfirm() { SendMenu(0); }
	void UpdateHangar(float Dt);
	void HangarZoomIn();
	void HangarZoomOut();
	void HangarToggleAutoRotate();
	void HangarBack();
	void HangarConfirm();
	void InputHangarPitch(float Value) { HangarPitchInput = FMath::Clamp(Value, -1.0f, 1.0f); }
	void InputHangarYaw(float Value) { HangarYawInput = FMath::Clamp(Value, -10.0f, 10.0f); }
	void InputHangarOrbit(float Value) { HangarOrbitInput = FMath::Clamp(Value, -1.0f, 1.0f); }
	void InputHangarZoom(float Value) { HangarZoomInput = FMath::Clamp(Value, -1.0f, 1.0f); }
	void HangarTabPrev();
	void HangarTabNext();
	void HangarClear();
	void HangarInsure();
	void HangarLaunch();
	void RefreshModuleVisuals();
	UStaticMesh* LoadPiece(const FString& Ship, const FString& Piece);
	/** Fuel, heat, repairs and the stabiliser, every frame of a race. */
	void UpdateRaceSystems(float Dt);
	/** Top speed against MaxSpeedMps now: no fuel, overheating, a repair under way, the REDLINE-X perk. */
	float SpeedCapMul() const;
	void SendMenu(int32 Step);
	void DriveBot(float Dt);
	void LoseLife();
	void RespawnOnRoute();
	void ApplyShipStats();

	FVector VelocityCmps = FVector::ZeroVector;
	FVector Heading = FVector::ForwardVector;
	FVector SurfaceUp = FVector::UpVector;
	FVector StartLocation = FVector::ZeroVector;
	FRotator StartRotation = FRotator::ZeroRotator;
	float ThrottleInput = 0.0f, BrakeInput = 0.0f, SteerInput = 0.0f, SteerVisual = 0.0f;
	bool bBoostHeld = false, bDriftHeld = false, bBoosting = false, bDrifting = false, bBraking = false, bGrounded = false, bLost = false;
	float HeightM = 0.0f, Nitro = 1.0f, ForwardSpeedMps = 0.0f, LateralSpeedMps = 0.0f, LongAccelMps2 = 0.0f;
	float YawRate = 0.0f, GripBlend = 1.0f, SlipRad = 0.0f, DriftCharge = 0.0f, MiniTurboFlash = 0.0f;
	float AirTimeSeconds = 0.0f, ImpactShake = 0.0f, SparkCooldown = 0.0f;
	float VisualRoll = 0.0f, VisualPitch = 0.0f, VisualYaw = 0.0f, HoverBobTime = 0.0f;
	int32 ShipIndex = 0, CameraMode = 0;

	// Chase camera state (ported from the previous game's chase camera).
	bool bCamInitialized = false, bCamWasBoosting = false;
	FVector CamOffsetCm = FVector::ZeroVector, CamSmoothUp = FVector::UpVector, CamSmoothHeading = FVector::ForwardVector;
	float CamFovV = 62.0f, CamKick = 0.0f, CamKickVel = 0.0f, CamBoostPunch = 0.0f, CamDriftSwing = 0.0f, CamLastSpeed = 0.0f;
	float LookYawInput = 0.0f, CamLookYaw = 0.0f, CamJolt = 0.0f, CamJoltTime = 0.0f, CamApexYaw = 0.0f, WallThreat = 0.0f;
	FVector GroundPointCm = FVector::ZeroVector;
	bool bLookBack = false;

	// Automated flight test (-EXFlightTest): scripted inputs, screenshots and telemetry log.
	bool bFlightTest = false, bTestWallPlaced = false, bDesertTest = false;
	int32 TestPathIndex = 0;
	/** The map's own race line (a spline tagged EXRoute), sampled every 5 m, in metres; empty on maps without one. */
	TArray<FVector2D> MapRoute;
	/** Nearest race line sample to the craft, followed every frame. */
	int32 RouteIndex = 0;
	float TestStuckSeconds = 0.0f;
	float TestTime = 0.0f, NextTestLog = 0.0f, TestDriftStart = -1.0f;
	int32 TestShotMask = 0;

	// Camera tour of the sector (-EXFlightTest -EXTour): fixed viewpoints of the geology, one screenshot each.
	bool bTour = false;
	/** -EXLook="x,y,z,yaw,pitch;..." (Unreal metres, degrees): views that replace the S01 tour on any map. */
	TArray<TPair<FVector, FRotator>> LookViews;
	FVector TourCameraLocation = FVector::ZeroVector;
	FRotator TourCameraRotation = FRotator::ZeroRotator;

	// Race rules state.
	bool bRaceRules = false, bBot = false, bRaceHold = false, bShipLocked = false, bEliminated = false;
	int32 Lives = 0, MaxLives = 0;
	float BaseMaxSpeedMps = 0.0f, WallHitMps = 1.0e6f, LandingHitMps = 1.0e6f;
	float HitCooldown = 0.0f, LastHitTime = -1.0f, RaceProgressM = 0.0f;
	// The tuned handling before the modules (BeginPlay), so the module stats never compound.
	float BaseAccelMps2 = 0.0f, BaseBoostAccelMps2 = 0.0f, BaseTurnLow = 0.0f, BaseTurnHigh = 0.0f, BaseGripRedirect = 0.0f;
	float BaseGripLateralMax = 0.0f, BaseNitroSeconds = 0.0f;
	// Modules, consumables, fuel and heat.
	TArray<FEXItem> Modules;
	TArray<FEXQuickSlot> QuickSlots;
	int32 ResolvedStats[EXMeta::StatCount] = {};
	float Fuel = 100.0f, Heat = 0.0f, RepairLeft = 0.0f, RepairTotal = 0.0f, RepairSlow = 0.0f, StabLeft = 0.0f;
	float LastQuickTime = -100.0f, QuickCooldown = 0.0f;
	float FuelBurnPerKm = 1.2f, HeatCoolPerS = 8.0f, BoostHeatPerS = 14.0f, RepairTimeMul = 1.0f;
	bool bOverheated = false, bRedline = false, bXRay = false;
	int32 LastQuickSlot = -1, AppliedHangarVersion = -1, AppliedHangarShip = -1;
	float PreviewEnginePower = 0.0f, HangarOrbitInput = 0.0f, HangarZoomInput = 0.0f;
	/** The module pieces on the hull: wings, tail, armour (the body kit), cooling, and the utility module inside the
	 *  nose, which only the x-ray view shows (attached to ShipMesh, no offset). */
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> ModuleMeshes;
	/** The x-ray view: structure, engines, reactor, cockpit, without the bodywork. */
	UPROPERTY() TObjectPtr<UStaticMeshComponent> SkeletonMesh;
	UPROPERTY() TObjectPtr<UMaterialInterface> GlowMaterial;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ReactorGlow;
	UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> UtilityGlow;
	/** /Game/Ships/<SHIP>/SM_<SHIP>_<piece>, loaded once (a missing piece is remembered as null). */
	UPROPERTY(Transient) TMap<FString, TObjectPtr<UStaticMesh>> PieceCache;
	UPROPERTY(Transient) TObjectPtr<UEXHangarModel> HangarModel;
	float LastGroundZCm = 0.0f;
	/** Wall closeness on each side (0 far, 1 touching), from the camera's wall probes; the sound uses them. */
	float WallNearLeft = 0.0f, WallNearRight = 0.0f, AudioHitCooldown = 0.0f;
	// Hangar and cargo.
	UPROPERTY(Transient) TObjectPtr<UEXProfileSave> Profile;
	UPROPERTY(Transient) TObjectPtr<AEXHangarStage> HangarStage;
	FVector PreHangarLocation = FVector::ZeroVector;
	FRotator PreHangarRotation = FRotator::ZeroRotator;
	bool bInShowroom = false, bQtyArmed = true, bZoomArmed = true;
	/** The orbit camera's distance now (it glides to HangarOrbitDist). */
	float HangarCamDist = 1250.0f;
	/** The frame the hangar was closed with Esc (the same press must not also quit from the menu). */
	uint64 HangarBackFrame = 0;
	float HangarYawInput = 0.0f;
	void FillAudioOthers(FEXCraftAudioInput& Sound) const;
	float BotSkill = 1.0f, BotLaneM = 0.0f, BotPhase = 0.0f, BotStuckSeconds = 0.0f, BotTime = 0.0f;

	// Hangar mode state.
	bool bInHangar = false, bHangarAutoRotate = true;
	float HangarOrbitYaw = 40.0f, HangarOrbitPitch = 14.0f, HangarOrbitDist = 680.0f;
	float HangarIdleTime = 0.0f, HangarPitchInput = 0.0f;
};
