#include "Game/EXHangarModel.h"

#include "Engine/World.h"
#include "Flight/EXHoverCraft.h"
#include "Game/EXProfile.h"

namespace
{
	constexpr int32 HangarTabCount = static_cast<int32>(EEXHangarTab::Count);
	constexpr float HangarRevealSeconds = 0.4f;
	constexpr float HangarSellConfirmSeconds = 3.0f;

	/** What the roster and the title say about each ship (the mock-up the player approved). */
	struct FHangarShipWords
	{
		const TCHAR* Name;
		const TCHAR* Role;
		const TCHAR* Subtitle;
	};
	const FHangarShipWords HangarShipWords[] = {
		{ TEXT("STRIX"), TEXT("INTERCEPTOR \u00B7 EQUILIBRADO"), TEXT("INTERCEPTOR  \u00B7  UM MOTOR CENTRAL, ASAS EM QUEDA") },
		{ TEXT("WRAITH"), TEXT("CA\u00C7A EM U \u00B7 R\u00C1PIDO"), TEXT("CA\u00C7A EM FORQUILHA  \u00B7  3 MOTORES DE PLASMA") },
		{ TEXT("NOMAD"), TEXT("DROPSHIP \u00B7 RESIST\u00CANCIA"), TEXT("DROPSHIP  \u00B7  4 MOTORES EM BRA\u00C7OS") },
		{ TEXT("BASTION"), TEXT("BLINDADO \u00B7 O MAIS RESISTENTE"), TEXT("ASA BLINDADA  \u00B7  MOTOR COLOSSAL, AIRBAGS DE IMPACTO") },
		{ TEXT("VORTEX"), TEXT("DELTA \u00B7 O MAIS R\u00C1PIDO, FR\u00C1GIL"), TEXT("ASA VOADORA  \u00B7  MOTOR EMBUTIDO NA CAUDA") },
	};

	const FHangarShipWords& HangarWordsFor(const FString& Ship)
	{
		for (const FHangarShipWords& Entry : HangarShipWords)
		{
			if (Ship.Contains(Entry.Name))
			{
				return Entry;
			}
		}
		return HangarShipWords[0];
	}

	const TCHAR* const HangarQuickKeys[EXMeta::QuickSlots] = { TEXT("1  \u00B7  \u25B2"), TEXT("2  \u00B7  \u25BC"), TEXT("3  \u00B7  \u25C0"), TEXT("4  \u00B7  \u25B6") };

	/** The short look of a piece (the line under a module's name) and the note pinned next to it on the ship. */
	struct FHangarLook
	{
		const TCHAR* Piece;
		const TCHAR* Short;
		const TCHAR* Callout;
	};
	const FHangarLook HangarLooks[] = {
		{ TEXT("wing_blade"), TEXT("barbatana na ponta"), TEXT("asa curta e enflechada \u00B7 barbatana na ponta") },
		{ TEXT("wing_longspan"), TEXT("placas na ponta"), TEXT("asa longa \u00B7 placas na ponta") },
		{ TEXT("wing_vector"), TEXT("segunda superf\u00EDcie"), TEXT("segunda superf\u00EDcie por cima") },
		{ TEXT("wing_brace"), TEXT("escora at\u00E9 ao casco"), TEXT("asa grossa \u00B7 escora at\u00E9 ao casco") },
		{ TEXT("wing_glide"), TEXT("ponta dobrada"), TEXT("ponta dobrada \u00B7 bordo de ataque luminoso") },
		{ TEXT("armor_light"), TEXT("kit de carro\u00E7aria leve"), TEXT("saias finas \u00B7 l\u00E2mina no nariz") },
		{ TEXT("armor_guard"), TEXT("kit de carro\u00E7aria"), TEXT("saias em placas \u00B7 l\u00E2mina no nariz") },
		{ TEXT("armor_bulwark"), TEXT("kit de carro\u00E7aria pesado"), TEXT("saias grossas \u00B7 aletas atr\u00E1s") },
		{ TEXT("armor_shell"), TEXT("kit com grelha t\u00E9rmica"), TEXT("saias com grelha t\u00E9rmica") },
		{ TEXT("armor_aegis"), TEXT("kit lend\u00E1rio"), TEXT("saias douradas \u00B7 aletas atr\u00E1s") },
		{ TEXT("cooling_vents"), TEXT("grelhas no dorso"), TEXT("grelhas de ventila\u00E7\u00E3o") },
		{ TEXT("cooling_radiator"), TEXT("radiadores no dorso"), TEXT("radiadores no dorso") },
		{ TEXT("cooling_grid"), TEXT("grelha t\u00E9rmica"), TEXT("grelha t\u00E9rmica grande") },
		{ TEXT("tail_compact"), TEXT("cauda curta"), TEXT("cauda curta") },
		{ TEXT("tail_twin"), TEXT("cauda dupla"), TEXT("cauda dupla") },
		{ TEXT("tail_keel"), TEXT("quilha longa"), TEXT("quilha longa") },
		{ TEXT("utility_mast"), TEXT("dentro do nariz"), TEXT("scanner \u00B7 dentro do nariz") },
		{ TEXT("utility_dome"), TEXT("dentro do nariz"), TEXT("or\u00E1culo de rota \u00B7 dentro do nariz") },
		{ TEXT("utility_drone"), TEXT("dentro do nariz"), TEXT("drone \u00B7 dentro do nariz") },
	};
	// By EXMeta look: the engine's flame, the nitro of the propulsion, the reactor's glow.
	const TCHAR* const HangarFlameLooks[] = { TEXT("chama de s\u00E9rie"), TEXT("jato azul"), TEXT("cone ciano curto"),
		TEXT("scramjet \u00B7 diamantes de choque"), TEXT("jato violeta fino"), TEXT("chama larga laranja"), TEXT("feixe fino"), TEXT("chama vermelha") };
	const TCHAR* const HangarNitroLooks[] = { TEXT("nitro de s\u00E9rie"), TEXT("nitro ciano"), TEXT("nitro azul"), TEXT("nitro violeta") };
	const TCHAR* const HangarReactorLooks[] = { TEXT("brilho laranja"), TEXT("brilho ciano"), TEXT("brilho azul"), TEXT("brilho magenta"),
		TEXT("brilho \u00E2mbar"), TEXT("brilho dourado") };
	// The family on a card ("Blindagem  ·  M  ·  +90 kg").
	const TCHAR* const HangarFamilyWords[] = { TEXT("Motor"), TEXT("Propuls\u00E3o"), TEXT("Asas"), TEXT("Cauda"), TEXT("Blindagem"), TEXT("Reator"),
		TEXT("Refrigera\u00E7\u00E3o"), TEXT("Utilidade") };
	// The chip of each consumable on a card (mock-up cofre.png), by EEXConsumable.
	const TCHAR* const HangarConsumableChips[] = { TEXT(""), TEXT("\u221245 calor"), TEXT("+1 vida"), TEXT("+30% combust\u00EDvel"), TEXT("+8 s ader\u00EAncia"),
		TEXT("+70% nitro"), TEXT("+1 vida em 2,5 s") };

	const TCHAR* HangarLookOf(const EXMeta::FModuleDef& Def, bool bCallout)
	{
		const int32 Look = Def.Look;
		switch (Def.Family)
		{
		case EEXFamily::Engine: return HangarFlameLooks[FMath::Clamp(Look, 0, static_cast<int32>(UE_ARRAY_COUNT(HangarFlameLooks)) - 1)];
		case EEXFamily::Propulsion: return HangarNitroLooks[FMath::Clamp(Look, 0, static_cast<int32>(UE_ARRAY_COUNT(HangarNitroLooks)) - 1)];
		case EEXFamily::Reactor: return HangarReactorLooks[FMath::Clamp(Look, 0, static_cast<int32>(UE_ARRAY_COUNT(HangarReactorLooks)) - 1)];
		default:
			for (const FHangarLook& Entry : HangarLooks)
			{
				if (Def.Piece.Equals(Entry.Piece))
				{
					return bCallout ? Entry.Callout : Entry.Short;
				}
			}
			return TEXT("");
		}
	}

	/** The photo of the module on the ship where it goes (Scripts/render_modules.py, thumbs): the ship's own one for its
	 *  wings, else the ship on the turntable. */
	FString HangarThumbKey(const EXMeta::FModuleDef& Def, const FString& Ship)
	{
		const FString On = (Def.Ship.IsEmpty() ? Ship : Def.Ship).ToLower();
		switch (Def.Family)
		{
		case EEXFamily::Engine: return FString::Printf(TEXT("%s_engine_%d"), *On, FMath::Clamp(Def.Look, 0, 7));
		case EEXFamily::Propulsion: return FString::Printf(TEXT("%s_prop_%d"), *On, FMath::Clamp(Def.Look, 0, 3));
		case EEXFamily::Reactor: return FString::Printf(TEXT("%s_reactor_%d"), *On, FMath::Clamp(Def.Look, 0, 5));
		default: return Def.Piece.IsEmpty() ? FString() : FString::Printf(TEXT("%s_%s"), *On, *Def.Piece);
		}
	}

	/** "+9 Manobra"-style chips: the gains first, then the drawbacks (mass left out), then the legendary's perk. */
	void HangarChips(const FEXItem& Item, bool bCard, TArray<FEXHangarChip>& Out)
	{
		for (int32 Pass = 0; Pass < 2; ++Pass)
		{
			for (int32 Stat = 0; Stat < EXMeta::StatCount && Stat < Item.Rolls.Num(); ++Stat)
			{
				const int32 V = Item.Rolls[Stat];
				if (Stat == static_cast<int32>(EEXStat::Mass) || V == 0 || (Pass == 0) != (V > 0))
				{
					continue;
				}
				const FString Name = bCard ? EXMeta::StatCard(static_cast<EEXStat>(Stat)) : EXMeta::StatName(static_cast<EEXStat>(Stat));
				FEXHangarChip& Chip = Out.AddDefaulted_GetRef();
				Chip.Text = V > 0 ? FString::Printf(TEXT("+%d %s"), V, *Name) : FString::Printf(TEXT("\u2212%d %s"), -V, *Name);
				Chip.Sign = V > 0 ? 1 : -1;
			}
		}
		const EXMeta::FModuleDef* Def = EXMeta::Find(Item);
		if (Def && Def->bLegendary && !bCard)
		{
			TArray<FString> Parts;
			Def->PerkText.ParseIntoArray(Parts, TEXT(" \u00B7 "));
			for (int32 Index = 1; Index < Parts.Num(); ++Index)
			{
				FEXHangarChip& Chip = Out.AddDefaulted_GetRef();
				Chip.Text = Parts[Index];
				Chip.Sign = 0;
			}
		}
	}

	FString HangarMass(int32 Kg)
	{
		return Kg == 0 ? FString() : (Kg > 0 ? FString::Printf(TEXT("  \u00B7  +%d kg"), Kg) : FString::Printf(TEXT("  \u00B7  \u2212%d kg"), -Kg));
	}

	FLinearColor EXUiHangarSand()
	{
		return FLinearColor(FColor(0xA8, 0x8C, 0x6A));
	}

	FString HangarDust(int32 Value)
	{
		// 12500 -> "12 500" (a fixed separator, whatever the system's locale).
		FString Digits = FString::FromInt(FMath::Abs(Value));
		for (int32 At = Digits.Len() - 3; At > 0; At -= 3)
		{
			Digits.InsertAt(At, TEXT(" "));
		}
		return (Value < 0 ? TEXT("-") : TEXT("")) + Digits;
	}

}

void UEXHangarModel::Bind(AEXHoverCraft* InCraft)
{
	Craft = InCraft;
}

UEXProfileSave* UEXHangarModel::GetProfile() const
{
	return Craft ? Craft->GetProfile() : nullptr;
}

FString UEXHangarModel::GetShipName() const
{
	return Craft ? Craft->GetShipName().ToUpper() : FString();
}

void UEXHangarModel::Open()
{
	CurrentTab = EEXHangarTab::Ship;
	for (int32& R : Rows)
	{
		R = 0;
	}
	Rows[static_cast<int32>(EEXHangarTab::Ship)] = Craft ? Craft->GetShipIndex() : 0;
	bOpening = false;
	SellArmed = 0;
	SyncCandidate();
	if (UEXProfileSave* Profile = GetProfile())
	{
		EXEconomy::SanitizeQuick(Profile);
	}
	Touch();
}

FString UEXHangarModel::TabName(EEXHangarTab Tab)
{
	static const TCHAR* Names[] = { TEXT("NAVE"), TEXT("EQUIPAR"), TEXT("CONSUM\u00CDVEIS"), TEXT("LOJA"), TEXT("COFRE") };
	return Names[FMath::Clamp(static_cast<int32>(Tab), 0, HangarTabCount - 1)];
}

FString UEXHangarModel::ShipRole(const FString& Ship)
{
	return HangarWordsFor(Ship).Role;
}

FString UEXHangarModel::StarText(int32 Stars)
{
	FString Out;
	for (int32 Index = 0; Index < EXMeta::MaxStars; ++Index)
	{
		Out += Index < Stars ? TEXT("\u25C6") : TEXT("\u25C7");
	}
	return Out + FString::Printf(TEXT("  %d/%d ESTRELAS"), Stars, EXMeta::MaxStars);
}

FString UEXHangarModel::ShipSubtitle(const FString& Ship)
{
	return HangarWordsFor(Ship).Subtitle;
}

void UEXHangarModel::Note(const FString& Text)
{
	Notice = Text;
	NoticeTime = Craft && Craft->GetWorld() ? Craft->GetWorld()->GetTimeSeconds() : 0.0f;
}

void UEXHangarModel::SaveProfile()
{
	EXEconomy::Save(GetProfile());
}

int32 UEXHangarModel::RowCount() const
{
	const UEXProfileSave* Profile = GetProfile();
	switch (CurrentTab)
	{
	case EEXHangarTab::Ship: return Craft ? Craft->GetShipCount() : 0;
	case EEXHangarTab::Equip: return EXMeta::FamilyCount;
	case EEXHangarTab::Quick: return EXMeta::QuickSlots;
	case EEXHangarTab::Shop: return EXMeta::CacheCount + (Profile ? Profile->Shop.Num() : 0);
	case EEXHangarTab::Vault: return (Profile ? Profile->Caches.Num() : 0) + VaultItems().Num();
	default: return 0;
	}
}

TArray<int32> UEXHangarModel::Candidates() const
{
	TArray<int32> Out;
	Out.Add(0);
	const UEXProfileSave* Profile = GetProfile();
	if (!Profile)
	{
		return Out;
	}
	const FString Ship = GetShipName();
	const EEXFamily Slot = CurrentSlot();
	TArray<const FEXItem*> Fit;
	for (const FEXItem& Item : Profile->Items)
	{
		const EXMeta::FModuleDef* Def = EXMeta::Find(Item);
		if (Def && EXMeta::Fits(*Def, Ship, Slot))
		{
			Fit.Add(&Item);
		}
	}
	Fit.Sort([](const FEXItem& A, const FEXItem& B) { return A.Rarity != B.Rarity ? A.Rarity > B.Rarity : A.Value > B.Value; });
	for (const FEXItem* Item : Fit)
	{
		Out.Add(Item->Serial);
	}
	return Out;
}

int32 UEXHangarModel::CandidateSerial() const
{
	const TArray<int32> List = Candidates();
	return List.IsValidIndex(Candidate) ? List[Candidate] : 0;
}

void UEXHangarModel::SyncCandidate()
{
	// The cursor starts on what is fitted.
	const UEXProfileSave* Profile = GetProfile();
	const FEXBuild* Build = Profile ? Profile->FindBuild(GetShipName()) : nullptr;
	const int32 Fitted = Build && Build->Slots.IsValidIndex(static_cast<int32>(CurrentSlot())) ? Build->Slots[static_cast<int32>(CurrentSlot())] : 0;
	Candidate = FMath::Max(0, Candidates().IndexOfByKey(Fitted));
}

TArray<int32> UEXHangarModel::VaultItems() const
{
	TArray<int32> Out;
	const UEXProfileSave* Profile = GetProfile();
	if (!Profile)
	{
		return Out;
	}
	TArray<const FEXItem*> Sorted;
	for (const FEXItem& Item : Profile->Items)
	{
		Sorted.Add(&Item);
	}
	Sorted.Sort([](const FEXItem& A, const FEXItem& B) { return A.Rarity != B.Rarity ? A.Rarity > B.Rarity : A.Value > B.Value; });
	for (const FEXItem* Item : Sorted)
	{
		Out.Add(Item->Serial);
	}
	return Out;
}

const FEXItem* UEXHangarModel::LookedItem() const
{
	const UEXProfileSave* Profile = GetProfile();
	if (!Profile)
	{
		return nullptr;
	}
	if (CurrentTab == EEXHangarTab::Shop)
	{
		const int32 Index = RowOf(EEXHangarTab::Shop) - EXMeta::CacheCount;
		return Profile->Shop.IsValidIndex(Index) ? &Profile->Shop[Index] : nullptr;
	}
	if (CurrentTab == EEXHangarTab::Vault && !bOpening)
	{
		const int32 Index = RowOf(EEXHangarTab::Vault) - Profile->Caches.Num();
		const TArray<int32> Items = VaultItems();
		return Items.IsValidIndex(Index) ? Profile->FindItem(Items[Index]) : nullptr;
	}
	return nullptr;
}

TArray<FEXItem> UEXHangarModel::GetPreviewBuild() const
{
	const UEXProfileSave* Profile = GetProfile();
	TArray<FEXItem> Build;
	if (Profile)
	{
		Build = Profile->EquippedCopy(GetShipName());
	}
	Build.SetNum(EXMeta::FamilyCount);
	if (CurrentTab == EEXHangarTab::Equip)
	{
		const FEXItem* Item = Profile ? Profile->FindItem(CandidateSerial()) : nullptr;
		Build[static_cast<int32>(CurrentSlot())] = Item ? *Item : FEXItem();
	}
	else if (const FEXItem* Item = LookedItem())
	{
		// A module in the shop or the vault that fits this ship is shown on it.
		const EXMeta::FModuleDef* Def = EXMeta::Find(*Item);
		if (Def && EXMeta::Fits(*Def, GetShipName(), Def->Family))
		{
			Build[static_cast<int32>(Def->Family)] = *Item;
		}
	}
	return Build;
}

EEXFamily UEXHangarModel::GetFocus() const
{
	if (CurrentTab == EEXHangarTab::Equip)
	{
		return CurrentSlot();
	}
	if (const FEXItem* Item = LookedItem())
	{
		const EXMeta::FModuleDef* Def = EXMeta::Find(*Item);
		if (Def && EXMeta::Fits(*Def, GetShipName(), Def->Family))
		{
			return Def->Family;
		}
	}
	return EEXFamily::Wings;
}

void UEXHangarModel::GetStats(int32 (&Now)[EXMeta::StatCount], int32 (&Next)[EXMeta::StatCount], int32& LivesNow, int32& LivesNext) const
{
	const UEXProfileSave* Profile = GetProfile();
	const FString Ship = GetShipName();
	TArray<const FEXItem*> Fitted;
	if (Profile)
	{
		Fitted = Profile->Equipped(Ship);
	}
	const int32 Stars = Profile ? Profile->StarsOf(Ship) : 0;
	EXMeta::Resolve(Ship, Fitted, Now, Stars);
	const TArray<FEXItem> Preview = GetPreviewBuild();
	TArray<const FEXItem*> PreviewPointers;
	for (const FEXItem& Item : Preview)
	{
		PreviewPointers.Add(Item.IsValid() ? &Item : nullptr);
	}
	EXMeta::Resolve(Ship, PreviewPointers, Next, Stars);
	LivesNow = EXMeta::Lives(Ship, Now[static_cast<int32>(EEXStat::Hull)]);
	LivesNext = EXMeta::Lives(Ship, Next[static_cast<int32>(EEXStat::Hull)]);
}

// ------------------------------------------------------------------------------------------------------------ input

void UEXHangarModel::Tab(int32 Step)
{
	if (bOpening)
	{
		return;
	}
	CurrentTab = static_cast<EEXHangarTab>((static_cast<int32>(CurrentTab) + Step + HangarTabCount) % HangarTabCount);
	Row() = FMath::Clamp(Row(), 0, FMath::Max(0, RowCount() - 1));
	if (CurrentTab == EEXHangarTab::Ship && Craft)
	{
		Row() = Craft->GetShipIndex();
	}
	SellArmed = 0;
	SyncCandidate();
	Touch();
}

void UEXHangarModel::Move(int32 Step)
{
	if (bOpening)
	{
		return;
	}
	const int32 Count = RowCount();
	if (Count <= 0)
	{
		return;
	}
	if (CurrentTab == EEXHangarTab::Ship && Craft)
	{
		Row() = Craft->GetShipIndex();   // Tab and 1-5 change the ship too
	}
	Row() = (Row() + Step + Count) % Count;
	SellArmed = 0;
	if (CurrentTab == EEXHangarTab::Ship && Craft)
	{
		Craft->SelectShip(Row());
	}
	SyncCandidate();
	Touch();
}

void UEXHangarModel::Change(int32 Step)
{
	UEXProfileSave* Profile = GetProfile();
	if (bOpening || !Profile)
	{
		return;
	}
	if (CurrentTab == EEXHangarTab::Equip)
	{
		const int32 Count = Candidates().Num();
		if (Count <= 1)
		{
			Note(FString::Printf(TEXT("Sem pe\u00E7as para %s nesta nave: compra na LOJA ou abre caixas"), *EXMeta::FamilyName(CurrentSlot())));
			return;
		}
		Candidate = (Candidate + Step + Count) % Count;
		Touch();
		return;
	}
	if (CurrentTab == EEXHangarTab::Quick)
	{
		FEXQuickSlot& Slot = Profile->Quick[FMath::Clamp(Row(), 0, EXMeta::QuickSlots - 1)];
		const EEXConsumable Kind = static_cast<EEXConsumable>(Slot.Kind);
		if (Kind == EEXConsumable::None)
		{
			Note(TEXT("Escolhe o consum\u00EDvel com Enter"));
			return;
		}
		if (Step < 0)
		{
			Slot.Count = FMath::Max(0, Slot.Count - 1);
			SaveProfile();
			return;
		}
		if (Slot.Count >= EXMeta::PerQuickSlot)
		{
			Note(TEXT("No m\u00E1ximo 2 em cada slot"));
			return;
		}
		if (QuickAvailable(Row(), Kind) <= Slot.Count)
		{
			// Nothing left in the stock: one is bought.
			const EXMeta::FConsumableDef& Def = EXMeta::Consumable(Kind);
			if (Profile->Stardust < Def.Price)
			{
				Note(TEXT("STARDUST insuficiente"));
				return;
			}
			Profile->Stardust -= Def.Price;
			Profile->AddStock(Kind, 1);
			Note(FString::Printf(TEXT("Comprado: %s (%d STARDUST)"), Def.Name, Def.Price));
		}
		++Slot.Count;
		SaveProfile();
	}
}

int32 UEXHangarModel::QuickAvailable(int32 Slot, EEXConsumable Kind) const
{
	// The stock of this kind minus what the other quick slots already take.
	const UEXProfileSave* Profile = GetProfile();
	if (!Profile)
	{
		return 0;
	}
	int32 Free = Profile->StockOf(Kind);
	for (int32 Other = 0; Other < Profile->Quick.Num(); ++Other)
	{
		if (Other != Slot && Profile->Quick[Other].Kind == static_cast<uint8>(Kind))
		{
			Free -= Profile->Quick[Other].Count;
		}
	}
	return FMath::Max(0, Free);
}

void UEXHangarModel::Confirm()
{
	UEXProfileSave* Profile = GetProfile();
	if (!Profile)
	{
		return;
	}
	if (bOpening)
	{
		// The mock-up cofre.png: Enter turns over the next card, Space all of them; then Enter keeps everything.
		if (Revealed < Cards.Num())
		{
			++Revealed;
		}
		else
		{
			CloseCache();
		}
		return;
	}
	const FString Ship = GetShipName();
	switch (CurrentTab)
	{
	case EEXHangarTab::Ship:
		if (Craft)
		{
			Craft->LaunchFromHangar();
		}
		return;
	case EEXHangarTab::Equip:
	{
		const int32 Serial = CandidateSerial();
		const FEXItem* Item = Profile->FindItem(Serial);
		const FString Was = Profile->EquippedOn(Serial);
		Profile->Equip(Ship, CurrentSlot(), Serial);
		if (Item)
		{
			Note(!Was.IsEmpty() && !Was.Equals(Ship, ESearchCase::IgnoreCase)
				? FString::Printf(TEXT("Montada: %s (saiu da %s)"), *EXMeta::ItemLabel(*Item), *Was)
				: FString::Printf(TEXT("Montada: %s"), *EXMeta::ItemLabel(*Item)));
		}
		else
		{
			Note(FString::Printf(TEXT("%s de s\u00E9rie"), *EXMeta::FamilyName(CurrentSlot())));
		}
		SaveProfile();
		SyncCandidate();
		Touch();
		return;
	}
	case EEXHangarTab::Quick:
	{
		// Enter goes to the next consumable; the count keeps to what there is.
		FEXQuickSlot& Slot = Profile->Quick[FMath::Clamp(Row(), 0, EXMeta::QuickSlots - 1)];
		const int32 NextKind = Slot.Kind % (EXMeta::ConsumableCount - 1) + 1;
		Slot.Kind = static_cast<uint8>(NextKind);
		Slot.Count = FMath::Min(FMath::Max(Slot.Count, 1), QuickAvailable(Row(), static_cast<EEXConsumable>(NextKind)));
		Slot.Count = FMath::Min(Slot.Count, EXMeta::PerQuickSlot);
		if (Slot.Count == 0)
		{
			Note(TEXT("Sem stock deste: D compra um"));
		}
		SaveProfile();
		return;
	}
	case EEXHangarTab::Shop:
		BuyShop(Row());
		return;
	case EEXHangarTab::Vault:
	{
		if (Row() < Profile->Caches.Num())
		{
			OpenCache(Row());
			return;
		}
		const TArray<int32> Items = VaultItems();
		const int32 Index = Row() - Profile->Caches.Num();
		if (Items.IsValidIndex(Index))
		{
			SellItem(Items[Index]);
		}
		return;
	}
	default:
		return;
	}
}

void UEXHangarModel::Clear()
{
	UEXProfileSave* Profile = GetProfile();
	if (!Profile)
	{
		return;
	}
	if (bOpening)
	{
		if (Revealed >= Cards.Num())
		{
			SellCommons();   // the "VENDER COMUNS (25%)" button
		}
		return;
	}
	if (CurrentTab == EEXHangarTab::Equip)
	{
		Profile->Equip(GetShipName(), CurrentSlot(), 0);
		Note(FString::Printf(TEXT("%s de s\u00E9rie"), *EXMeta::FamilyName(CurrentSlot())));
		SaveProfile();
		SyncCandidate();
		Touch();
	}
	else if (CurrentTab == EEXHangarTab::Quick)
	{
		FEXQuickSlot& Slot = Profile->Quick[FMath::Clamp(Row(), 0, EXMeta::QuickSlots - 1)];
		Slot.Kind = 0;
		Slot.Count = 0;
		SaveProfile();
	}
}

void UEXHangarModel::Insure()
{
	UEXProfileSave* Profile = GetProfile();
	if (bOpening || !Profile || CurrentTab != EEXHangarTab::Equip)
	{
		return;
	}
	FEXBuild& Build = Profile->BuildFor(GetShipName());
	const int32 Fitted = Build.Slots[static_cast<int32>(CurrentSlot())];
	const FEXItem* Item = Profile->FindItem(Fitted);
	if (!Item)
	{
		Note(TEXT("S\u00F3 se segura uma pe\u00E7a montada"));
		return;
	}
	Build.Insured = Build.Insured == Fitted ? 0 : Fitted;
	Note(Build.Insured ? FString::Printf(TEXT("Segura: %s (nunca se perde)"), *EXMeta::ItemLabel(*Item)) : FString(TEXT("Sem seguro")));
	SaveProfile();
}

void UEXHangarModel::Alt()
{
	if (bOpening)
	{
		Revealed = Cards.Num();
	}
}

void UEXHangarModel::CloseCache()
{
	if (bOpening)
	{
		bOpening = false;
		Revealed = Cards.Num();
		Row() = FMath::Clamp(Row(), 0, FMath::Max(0, RowCount() - 1));
		Touch();
	}
}

void UEXHangarModel::Tick(float Dt)
{
	// Another ship (Tab, 1-5): the cursor goes back to what that ship has fitted.
	const FString Ship = GetShipName();
	if (Ship != ShownShip)
	{
		ShownShip = Ship;
		SyncCandidate();
		Touch();
	}
	// The cards wait for Enter (one) or Space (all), as in the mock-up; the first one turns over by itself.
	if (bOpening && Revealed == 0 && Cards.Num() > 0)
	{
		RevealTimer += Dt;
		if (RevealTimer >= HangarRevealSeconds)
		{
			Revealed = 1;
		}
	}
	if (SellArmed != 0 && Craft && Craft->GetWorld() && Craft->GetWorld()->GetTimeSeconds() - SellArmedTime > HangarSellConfirmSeconds)
	{
		SellArmed = 0;
	}
}

// ------------------------------------------------------------------------------------------------------------ shop and vault

void UEXHangarModel::BuyShop(int32 Index)
{
	UEXProfileSave* Profile = GetProfile();
	if (!Profile)
	{
		return;
	}
	if (Index < EXMeta::CacheCount)
	{
		const EXMeta::FCacheDef& Def = EXMeta::Cache(static_cast<EEXCache>(Index));
		if (Profile->Stardust < Def.Price)
		{
			Note(TEXT("STARDUST insuficiente"));
			return;
		}
		Profile->Stardust -= Def.Price;
		Profile->Caches.Add(static_cast<uint8>(Index));
		Note(FString::Printf(TEXT("Comprada: %s \u00B7 abre-a no COFRE"), Def.Name));
		SaveProfile();
		return;
	}
	const int32 Offer = Index - EXMeta::CacheCount;
	if (!Profile->Shop.IsValidIndex(Offer))
	{
		return;
	}
	const FEXItem Item = Profile->Shop[Offer];
	const int32 Price = EXMeta::ShopPrice(Item);
	if (Profile->Stardust < Price)
	{
		Note(TEXT("STARDUST insuficiente"));
		return;
	}
	Profile->Stardust -= Price;
	Profile->Items.Add(Item);
	Profile->Shop.RemoveAt(Offer);
	Note(FString::Printf(TEXT("Comprada: %s \u00B7 monta-a em EQUIPAR"), *EXMeta::ItemLabel(Item)));
	Row() = FMath::Clamp(Row(), 0, FMath::Max(0, RowCount() - 1));
	SaveProfile();
	Touch();
}

void UEXHangarModel::OpenCache(int32 Index)
{
	UEXProfileSave* Profile = GetProfile();
	if (!Profile || !Profile->Caches.IsValidIndex(Index))
	{
		return;
	}
	OpenedKind = static_cast<EEXCache>(FMath::Clamp(static_cast<int32>(Profile->Caches[Index]), 0, EXMeta::CacheCount - 1));
	Profile->Caches.RemoveAt(Index);
	FRandomStream Random = Profile->NextRandom();
	TArray<FEXItem> Got;
	TArray<EEXConsumable> Consumables;
	int32 ShipCopy = INDEX_NONE;
	EXMeta::OpenCache(OpenedKind, Random, Profile->NextSerial, Got, Consumables, &ShipCopy);
	Profile->Items.Append(Got);
	// The cards (mock-up cofre.png): the consumables first (one card per kind, "Coolant Cell ×2"), then the modules from
	// the plainest to the best (the best turns over last), a copy of a ship at the very end.
	Cards.Reset();
	CardSerials.Reset();
	CacheValue = 0;
	TArray<int32> PerKind;
	PerKind.Init(0, EXMeta::ConsumableCount);
	for (const EEXConsumable Kind : Consumables)
	{
		Profile->AddStock(Kind, 1);
		++PerKind[static_cast<int32>(Kind)];
		CacheValue += EXMeta::Consumable(Kind).Price;
	}
	for (int32 Kind = 1; Kind < EXMeta::ConsumableCount; ++Kind)
	{
		if (PerKind[Kind] == 0)
		{
			continue;
		}
		const EXMeta::FConsumableDef& Def = EXMeta::Consumable(static_cast<EEXConsumable>(Kind));
		FEXHangarRow& Card = Cards.AddDefaulted_GetRef();
		Card.Label = EXMeta::RarityName(EEXRarity::Common);
		Card.Title = FString::Printf(TEXT("%s \u00D7%d"), Def.Name, PerKind[Kind]);
		Card.Maker = TEXT("Consum\u00EDvel");
		Card.Sub = Def.Effect;
		Card.Colour = EXMeta::RarityColour(EEXRarity::Common);
		Card.Icon = FString::Printf(TEXT("con_%s"), Def.Id);
		Card.Value = Def.Price * PerKind[Kind];
		FEXHangarChip& Chip = Card.Chips.AddDefaulted_GetRef();
		Chip.Text = HangarConsumableChips[FMath::Clamp(Kind, 0, static_cast<int32>(UE_ARRAY_COUNT(HangarConsumableChips)) - 1)];
		Chip.Sign = Chip.Text.StartsWith(TEXT("+")) ? 1 : -1;
		CardSerials.Add(0);
	}
	Got.Sort([](const FEXItem& A, const FEXItem& B) { return A.Rarity != B.Rarity ? A.Rarity < B.Rarity : A.Value < B.Value; });
	for (const FEXItem& Item : Got)
	{
		Cards.Add(ItemCard(Item));
		CardSerials.Add(Item.Serial);
		CacheValue += Item.Value;
	}
	if (ShipCopy != INDEX_NONE)
	{
		// The last card, the rarest: a copy of a ship. It adds a star, or pays STARDUST if the ship is already at seven.
		const EXMeta::FShipDef& Def = EXMeta::ShipAt(ShipCopy);
		const FString ShipName(Def.Name);
		FEXHangarRow& Card = Cards.AddDefaulted_GetRef();
		Card.Label = TEXT("C\u00D3PIA DA NAVE");
		Card.Title = ShipName;
		Card.Colour = FLinearColor(1.0f, 0.82f, 0.20f);
		Card.Thumb = ShipName.ToLower() + TEXT("_ship");
		Card.Icon = TEXT("ship_copy");
		Card.bNew = true;
		CardSerials.Add(0);
		if (Profile->AddStar(ShipName))
		{
			const int32 Stars = Profile->StarsOf(ShipName);
			Card.Maker = UEXHangarModel::StarText(Stars);
			Card.Sub = Card.Maker;
			FEXHangarChip& Chip = Card.Chips.AddDefaulted_GetRef();
			Chip.Text = FString::Printf(TEXT("+%d em todos os stats base"), EXMeta::StarBonus(Stars) - EXMeta::StarBonus(Stars - 1));
			Chip.Sign = 1;
			Card.Right = FString::Printf(TEXT("%d/%d"), Stars, EXMeta::MaxStars);
			Card.Tag = TEXT("NOVA ESTRELA");
			Note(FString::Printf(TEXT("C\u00F3pia da %s: agora com %d estrelas"), *ShipName, Stars));
		}
		else
		{
			Profile->Stardust += EXMeta::ShipCopyRefund;
			Card.Maker = TEXT("J\u00E1 tem as 7 estrelas");
			Card.Sub = TEXT("J\u00E1 tem as 7 estrelas: a c\u00F3pia foi paga em STARDUST");
			Card.Value = EXMeta::ShipCopyRefund;
			Card.Tag = TEXT("REPETIDA");
		}
		UE_LOG(LogTemp, Display, TEXT("EXMETA SHIPCOPY %s stars=%d"), *ShipName, Profile->StarsOf(ShipName));
	}
	bOpening = true;
	Revealed = 0;
	RevealTimer = 0.0f;
	SaveProfile();
	Note(FString::Printf(TEXT("%s aberta: %d m\u00F3dulos e %d consum\u00EDveis"), EXMeta::Cache(OpenedKind).Name, Got.Num(), Consumables.Num()));
	UE_LOG(LogTemp, Display, TEXT("EXMETA CACHE %s modules=%d consumables=%d value=%d"), EXMeta::Cache(OpenedKind).Name, Got.Num(),
		Consumables.Num(), CacheValue);
}

void UEXHangarModel::SellItem(int32 Serial)
{
	UEXProfileSave* Profile = GetProfile();
	const FEXItem* Item = Profile ? Profile->FindItem(Serial) : nullptr;
	if (!Item)
	{
		return;
	}
	const int32 Price = EXMeta::SellValue(*Item);
	const float Now = Craft && Craft->GetWorld() ? Craft->GetWorld()->GetTimeSeconds() : 0.0f;
	if (SellArmed != Serial)
	{
		// The first Enter asks; the second, within three seconds, sells.
		SellArmed = Serial;
		SellArmedTime = Now;
		const FString On = Profile->EquippedOn(Serial);
		Note(On.IsEmpty() ? FString::Printf(TEXT("Enter outra vez para vender por %s STARDUST"), *HangarDust(Price))
			: FString::Printf(TEXT("Est\u00E1 montada na %s. Enter outra vez para vender por %s STARDUST"), *On, *HangarDust(Price)));
		return;
	}
	const FString Label = EXMeta::ItemLabel(*Item);
	Profile->Stardust += Price;
	Profile->RemoveItem(Serial);
	SellArmed = 0;
	Note(FString::Printf(TEXT("Vendida: %s (+%s STARDUST)"), *Label, *HangarDust(Price)));
	Row() = FMath::Clamp(Row(), 0, FMath::Max(0, RowCount() - 1));
	SaveProfile();
	Touch();
}

FString UEXHangarModel::GetCacheTitle() const
{
	return EXMeta::Cache(OpenedKind).Name;
}

int32 UEXHangarModel::GetCachePrice() const
{
	return EXMeta::Cache(OpenedKind).Price;
}

// ------------------------------------------------------------------------------------------------------------ lists

FEXHangarRow UEXHangarModel::ItemRow(const FEXItem& Item, bool bWithPlace) const
{
	FEXHangarRow R;
	const EXMeta::FModuleDef* Def = EXMeta::Find(Item);
	const EEXRarity Rarity = static_cast<EEXRarity>(Item.Rarity);
	R.Label = FString::Printf(TEXT("%s  \u00B7  %s"), *EXMeta::RarityName(Rarity), Def ? *EXMeta::FamilyName(Def->Family) : TEXT(""));
	R.Title = EXMeta::ItemLabel(Item);
	R.Sub = EXMeta::RollText(Item);
	R.Right = HangarDust(Item.Value);
	R.Colour = EXMeta::RarityColour(Rarity);
	R.Rarity = EXMeta::RarityName(Rarity);
	R.Value = Item.Value;
	R.bApprox = true;
	HangarChips(Item, false, R.Chips);
	if (Def)
	{
		R.Icon = FString::Printf(TEXT("fam_%d"), static_cast<int32>(Def->Family));
		R.Thumb = HangarThumbKey(*Def, GetShipName());
		R.Flame = Def->Family == EEXFamily::Engine ? EXMeta::FlameLook(&Item) : INDEX_NONE;
		// "Vanta Works  ·  classe S  ·  −10 kg", "Oryx Reclamation  ·  asa própria  ·  ponta dobrada"; a legendary's perk.
		if (Def->bLegendary)
		{
			TArray<FString> Parts;
			Def->PerkText.ParseIntoArray(Parts, TEXT(" \u00B7 "));
			R.Maker = FString::Printf(TEXT("%s  \u00B7  %s"), *Def->Maker, Parts.Num() > 0 ? *Parts[0] : TEXT(""));
		}
		else if (Def->Family == EEXFamily::Wings)
		{
			R.Maker = FString::Printf(TEXT("%s  \u00B7  asa pr\u00F3pria  \u00B7  %s"), *Def->Maker, HangarLookOf(*Def, false));
		}
		else
		{
			R.Maker = FString::Printf(TEXT("%s  \u00B7  classe %s%s"), *Def->Maker, *EXMeta::SizeText(Def->Size), *HangarMass(Item.Roll(EEXStat::Mass)));
		}
	}
	const UEXProfileSave* Profile = GetProfile();
	if (bWithPlace && Profile)
	{
		const FString On = Profile->EquippedOn(Item.Serial);
		if (!On.IsEmpty())
		{
			const FEXBuild* Build = Profile->FindBuild(On);
			const bool bInsured = Build && Build->Insured == Item.Serial;
			R.Tag = On.Equals(GetShipName(), ESearchCase::IgnoreCase) ? FString(bInsured ? TEXT("MONTADO \u00B7 SEGURO") : TEXT("MONTADO"))
				: FString::Printf(TEXT("NA %s"), *On);
			R.bInsured = bInsured;
		}
	}
	return R;
}

FEXHangarRow UEXHangarModel::ItemCard(const FEXItem& Item) const
{
	FEXHangarRow Card;
	const EXMeta::FModuleDef* Def = EXMeta::Find(Item);
	const EEXRarity Rarity = static_cast<EEXRarity>(Item.Rarity);
	Card.Label = EXMeta::RarityName(Rarity);
	Card.Rarity = Card.Label;
	Card.Title = EXMeta::ItemLabel(Item);
	Card.Colour = EXMeta::RarityColour(Rarity);
	Card.Value = Item.Value;
	Card.bNew = Rarity >= EEXRarity::Epic;
	HangarChips(Item, true, Card.Chips);
	if (Def)
	{
		Card.Icon = FString::Printf(TEXT("fam_%d"), static_cast<int32>(Def->Family));
		Card.Thumb = HangarThumbKey(*Def, GetShipName());
		Card.Flame = Def->Family == EEXFamily::Engine ? EXMeta::FlameLook(&Item) : INDEX_NONE;
		const FString Family = HangarFamilyWords[FMath::Clamp(static_cast<int32>(Def->Family), 0, EXMeta::FamilyCount - 1)];
		if (Def->Family == EEXFamily::Wings)
		{
			Card.Maker = FString::Printf(TEXT("Asa pr\u00F3pria  \u00B7  %s"), *Def->Ship);
		}
		else
		{
			const FString Look = (Def->Family == EEXFamily::Reactor || Def->Family == EEXFamily::Engine || Def->Family == EEXFamily::Propulsion)
				? FString::Printf(TEXT("  \u00B7  %s"), HangarLookOf(*Def, false)) : FString();
			Card.Maker = FString::Printf(TEXT("%s  \u00B7  %s%s%s"), *Family, *EXMeta::SizeText(Def->Size), *HangarMass(Item.Roll(EEXStat::Mass)), *Look);
		}
	}
	return Card;
}

void UEXHangarModel::BuildLeft(FString& Title, TArray<FEXHangarRow>& Out, int32& Selected) const
{
	Out.Reset();
	Selected = RowOf(CurrentTab);
	const UEXProfileSave* Profile = GetProfile();
	const FString Ship = GetShipName();
	switch (CurrentTab)
	{
	case EEXHangarTab::Ship:
	{
		Title = TEXT("NAVES");
		const int32 Count = Craft ? Craft->GetShipCount() : 0;
		for (int32 Index = 0; Index < Count; ++Index)
		{
			const FString Name = Craft->GetShipNameAt(Index).ToUpper();
			int32 ShipLives = 3;
			if (Profile)
			{
				int32 Stats[EXMeta::StatCount];
				EXMeta::Resolve(Name, Profile->Equipped(Name), Stats, Profile->StarsOf(Name));
				ShipLives = EXMeta::Lives(Name, Stats[static_cast<int32>(EEXStat::Hull)]);
			}
			FEXHangarRow& R = Out.AddDefaulted_GetRef();
			R.Label = ShipRole(Name);
			R.Title = Name;
			R.Right = FString::Printf(TEXT("%d VIDAS"), ShipLives);
			R.Colour = FLinearColor(1.0f, 0.34f, 0.10f);
			R.Lives = ShipLives;
			R.Stars = Profile ? Profile->StarsOf(Name) : 0;
			R.Thumb = Name.ToLower() + TEXT("_ship");
		}
		Selected = Craft ? Craft->GetShipIndex() : 0;
		return;
	}
	case EEXHangarTab::Equip:
	{
		Title = FString::Printf(TEXT("SLOTS DA NAVE  \u00B7  %s"), *Ship);
		const TArray<const FEXItem*> Fitted = Profile ? Profile->Equipped(Ship) : TArray<const FEXItem*>();
		const FEXBuild* Build = Profile ? Profile->FindBuild(Ship) : nullptr;
		const EXMeta::FShipDef& Def = EXMeta::Ship(Ship);
		for (int32 Slot = 0; Slot < EXMeta::FamilyCount; ++Slot)
		{
			FEXHangarRow& R = Out.AddDefaulted_GetRef();
			const FEXItem* Item = Fitted.IsValidIndex(Slot) ? Fitted[Slot] : nullptr;
			R.Label = EXMeta::FamilyName(static_cast<EEXFamily>(Slot));
			R.Icon = FString::Printf(TEXT("fam_%d"), Slot);
			R.Right = Def.Sizes[Slot] == EXMeta::SizeAny && Slot == static_cast<int32>(EEXFamily::Wings) ? FString(TEXT("PR\u00D3PRIAS"))
				: EXMeta::SizeText(Def.Sizes[Slot]);

			if (Def.Sizes[Slot] == 0)
			{
				R.Title = TEXT("\u2014");
				R.bDim = true;
				R.Colour = FLinearColor(0.3f, 0.3f, 0.3f);
				continue;
			}
			R.Title = Item ? EXMeta::ItemLabel(*Item) : FString(TEXT("De s\u00E9rie"));
			R.Sub = Item ? EXMeta::RollText(*Item) : FString();
			// The class badge: the fitted module's size (the slot's for the stock part); none when any size goes.
			const EXMeta::FModuleDef* ItemDef = Item ? EXMeta::Find(*Item) : nullptr;
			const uint8 Badge = ItemDef ? ItemDef->Size : Def.Sizes[Slot];
			R.Size = Badge == EXMeta::SizeAny ? FString() : EXMeta::SizeText(Badge);
			R.Colour = Item ? EXMeta::RarityColour(static_cast<EEXRarity>(Item->Rarity)) : FLinearColor(0.42f, 0.36f, 0.30f);
			R.bInsured = Item && Build && Build->Insured == Item->Serial;
			R.Tag = R.bInsured ? FString(TEXT("SEGURA")) : FString();
		}
		return;
	}
	case EEXHangarTab::Quick:
	{
		Title = TEXT("4 SLOTS R\u00C1PIDOS  \u00B7  AT\u00C9 2 DE CADA");
		for (int32 Slot = 0; Slot < EXMeta::QuickSlots; ++Slot)
		{
			const FEXQuickSlot Q = Profile && Profile->Quick.IsValidIndex(Slot) ? Profile->Quick[Slot] : FEXQuickSlot();
			const EEXConsumable Kind = static_cast<EEXConsumable>(Q.Kind);
			const EXMeta::FConsumableDef& Def = EXMeta::Consumable(Kind);
			FEXHangarRow& R = Out.AddDefaulted_GetRef();
			R.Label = HangarQuickKeys[Slot];
			R.Title = Kind == EEXConsumable::None ? FString(TEXT("Vazio")) : FString(Def.Name);
			R.Sub = Def.Effect;
			R.Right = Kind == EEXConsumable::None ? FString() : FString::Printf(TEXT("\u00D7%d"), Q.Count);
			R.Colour = Def.Colour;
			R.bDim = Kind == EEXConsumable::None || Q.Count == 0;
			R.Icon = Kind == EEXConsumable::None ? FString() : FString::Printf(TEXT("con_%s"), Def.Id);
			R.Count = Kind == EEXConsumable::None ? 0 : Q.Count;
			R.MaxCount = EXMeta::PerQuickSlot;
		}
		return;
	}
	case EEXHangarTab::Shop:
	{
		Title = TEXT("LOJA  \u00B7  MUDA A CADA EXPEDI\u00C7\u00C3O");
		for (int32 Kind = 0; Kind < EXMeta::CacheCount; ++Kind)
		{
			const EXMeta::FCacheDef& Def = EXMeta::Cache(static_cast<EEXCache>(Kind));
			FEXHangarRow& R = Out.AddDefaulted_GetRef();
			R.Label = TEXT("CAIXA");
			R.Title = Def.Name;
			R.Sub = Def.Promise;
			R.Maker = Def.Promise;
			R.Right = HangarDust(Def.Price);
			R.Colour = FLinearColor(1.0f, 0.34f, 0.10f);
			R.bDim = Profile && Profile->Stardust < Def.Price;
			R.Icon = FString::Printf(TEXT("cache_%d"), Kind);
			R.Value = Def.Price;
		}
		for (int32 Offer = 0; Profile && Offer < Profile->Shop.Num(); ++Offer)
		{
			FEXHangarRow R = ItemRow(Profile->Shop[Offer], false);
			R.Right = HangarDust(EXMeta::ShopPrice(Profile->Shop[Offer]));
			R.bDim = Profile->Stardust < EXMeta::ShopPrice(Profile->Shop[Offer]);
			R.Value = EXMeta::ShopPrice(Profile->Shop[Offer]);
			R.bApprox = false;
			Out.Add(R);
		}
		return;
	}
	case EEXHangarTab::Vault:
	{
		Title = TEXT("COFRE");
		for (int32 Index = 0; Profile && Index < Profile->Caches.Num(); ++Index)
		{
			const EXMeta::FCacheDef& Def = EXMeta::Cache(static_cast<EEXCache>(FMath::Min(static_cast<int32>(Profile->Caches[Index]), EXMeta::CacheCount - 1)));
			FEXHangarRow& R = Out.AddDefaulted_GetRef();
			R.Label = TEXT("CAIXA POR ABRIR");
			R.Title = Def.Name;
			R.Sub = Def.Promise;
			R.Maker = Def.Promise;
			R.Right = TEXT("ABRIR");
			R.Colour = FLinearColor(1.0f, 0.34f, 0.10f);
			R.Icon = FString::Printf(TEXT("cache_%d"), FMath::Min(static_cast<int32>(Profile->Caches[Index]), EXMeta::CacheCount - 1));
			R.Tag = TEXT("ABRIR");
		}
		for (const int32 Serial : VaultItems())
		{
			if (const FEXItem* Item = Profile->FindItem(Serial))
			{
				Out.Add(ItemRow(*Item, true));
			}
		}
		return;
	}
	default:
		return;
	}
}

void UEXHangarModel::BuildRight(FString& Title, TArray<FEXHangarRow>& Out, int32& Selected, FString& Detail) const
{
	Out.Reset();
	Selected = -1;
	Detail.Reset();
	const UEXProfileSave* Profile = GetProfile();
	const FString Ship = GetShipName();
	auto Line = [&Out](const FString& Label, const FString& Value, const FString& Sub, const FLinearColor& Colour)
	{
		FEXHangarRow& R = Out.AddDefaulted_GetRef();
		R.Label = Label;
		R.Title = Value;
		R.Sub = Sub;
		R.Colour = Colour;
	};
	auto DescribeItem = [&](const FEXItem& Item, FString& Text)
	{
		const EXMeta::FModuleDef* Def = EXMeta::Find(Item);
		if (!Def)
		{
			return;
		}
		Text = FString::Printf(TEXT("%s  \u00B7  %s  \u00B7  classe %s  \u00B7  massa %+d kg\n%s"), *Def->Maker, *EXMeta::FamilyName(Def->Family),
			*EXMeta::SizeText(Def->Size), Item.Roll(EEXStat::Mass), *Def->Description);
		if (Def->bLegendary)
		{
			Text += FString::Printf(TEXT("\nPERK: %s"), *Def->PerkText);
		}
		if (!Def->Ship.IsEmpty())
		{
			Text += FString::Printf(TEXT("\nS\u00F3 serve na %s."), *Def->Ship);
		}
		else if (!EXMeta::Fits(*Def, Ship, Def->Family))
		{
			Text += FString::Printf(TEXT("\nN\u00E3o cabe na %s (slot %s)."), *Ship, *EXMeta::SizeText(EXMeta::Ship(Ship).Sizes[static_cast<int32>(Def->Family)]));
		}
	};
	switch (CurrentTab)
	{
	case EEXHangarTab::Ship:
	{
		const EXMeta::FShipDef& Def = EXMeta::Ship(Ship);
		Title = Ship;
		Line(TEXT("PASSIVA"), Def.Passive, Def.PassiveText, FLinearColor(1.0f, 0.34f, 0.10f));
		int32 Fitted = 0;
		for (const FEXItem* Item : Profile ? Profile->Equipped(Ship) : TArray<const FEXItem*>())
		{
			Fitted += Item ? 1 : 0;
		}
		Line(TEXT("M\u00D3DULOS"), FString::Printf(TEXT("%d de %d montados"), Fitted, EXMeta::FamilyCount), TEXT("muda-os em EQUIPAR"), FLinearColor(0.3f, 0.6f, 1.0f));
		Line(TEXT("EM RISCO"), FString::Printf(TEXT("%s STARDUST"), *HangarDust(EXEconomy::RiskValue(Profile, Ship))),
			TEXT("at\u00E9 3 m\u00F3dulos (n\u00E3o o seguro) e os consum\u00EDveis, se fores destru\u00EDdo"), FLinearColor(1.0f, 0.48f, 0.23f));
		Detail = TEXT("Enter lan\u00E7a a expedi\u00E7\u00E3o. Chega a B vivo para ficares com tudo e com a tua parte do esp\u00F3lio.");
		return;
	}
	case EEXHangarTab::Equip:
	{
		const TArray<int32> List = Candidates();
		Title = FString::Printf(TEXT("%s  \u00B7  %d NO INVENT\u00C1RIO"), *EXMeta::FamilyName(CurrentSlot()), List.Num() - 1);
		const FEXBuild* Build = Profile ? Profile->FindBuild(Ship) : nullptr;
		const int32 FittedSerial = Build && Build->Slots.IsValidIndex(static_cast<int32>(CurrentSlot())) ? Build->Slots[static_cast<int32>(CurrentSlot())] : 0;
		for (const int32 Serial : List)
		{
			const FEXItem* Item = Profile ? Profile->FindItem(Serial) : nullptr;
			if (!Item)
			{
				FEXHangarRow& R = Out.AddDefaulted_GetRef();
				R.Label = TEXT("PE\u00C7A DA NAVE");
				R.Title = TEXT("De s\u00E9rie");
				R.Sub = TEXT("sem b\u00F3nus, nunca se perde");
				R.Maker = R.Sub;
				R.Rarity = TEXT("DE S\u00C9RIE");
				R.Colour = FLinearColor(0.42f, 0.36f, 0.30f);
				R.Tag = FittedSerial == 0 ? FString(TEXT("MONTADO")) : FString();
				R.Icon = FString::Printf(TEXT("fam_%d"), static_cast<int32>(CurrentSlot()));
				continue;
			}
			Out.Add(ItemRow(*Item, true));
		}
		Selected = Candidate;
		if (const FEXItem* Item = Profile ? Profile->FindItem(CandidateSerial()) : nullptr)
		{
			DescribeItem(*Item, Detail);
		}
		else
		{
			Detail = TEXT("A pe\u00E7a com que a nave sai da f\u00E1brica.");
		}
		return;
	}
	case EEXHangarTab::Quick:
	{
		Title = TEXT("STOCK SEGURO  \u00B7  FICA NO HANGAR");
		for (int32 Kind = 1; Kind < EXMeta::ConsumableCount; ++Kind)
		{
			const EXMeta::FConsumableDef& Def = EXMeta::Consumable(static_cast<EEXConsumable>(Kind));
			FEXHangarRow& R = Out.AddDefaulted_GetRef();
			R.Label = FString::Printf(TEXT("%d STARDUST"), Def.Price);
			R.Title = Def.Name;
			R.Sub = Def.Effect;
			R.Maker = Def.Effect;
			R.Right = FString::Printf(TEXT("\u00D7%d"), Profile ? Profile->StockOf(static_cast<EEXConsumable>(Kind)) : 0);
			R.Colour = Def.Colour;
			R.Icon = FString::Printf(TEXT("con_%s"), Def.Id);
			R.Count = Profile ? Profile->StockOf(static_cast<EEXConsumable>(Kind)) : 0;
			R.Button = FString::Printf(TEXT("COMPRAR %d"), Def.Price);
			R.Value = Def.Price;
			if (Profile && Profile->Quick.IsValidIndex(RowOf(EEXHangarTab::Quick)) && Profile->Quick[RowOf(EEXHangarTab::Quick)].Kind == Kind)
			{
				Selected = Kind - 1;
			}
		}
		int32 Carried = 0;
		for (int32 Slot = 0; Profile && Slot < Profile->Quick.Num(); ++Slot)
		{
			Carried += Profile->Quick[Slot].Count;
		}
		Detail = FString::Printf(TEXT("Levas %d consum\u00EDveis (%s STARDUST). Se fores destru\u00EDdo perdes os que levas; se extra\u00EDres, os que n\u00E3o "
			"gastaste voltam ao stock."), Carried, *HangarDust(EXEconomy::QuickValue(Profile)));
		return;
	}
	case EEXHangarTab::Shop:
	case EEXHangarTab::Vault:
	{
		const int32 Index = RowOf(CurrentTab);
		const bool bShop = CurrentTab == EEXHangarTab::Shop;
		const int32 Caches = bShop ? EXMeta::CacheCount : (Profile ? Profile->Caches.Num() : 0);
		if (Index < Caches)
		{
			const EEXCache Kind = bShop ? static_cast<EEXCache>(Index)
				: static_cast<EEXCache>(Profile ? FMath::Min(static_cast<int32>(Profile->Caches[Index]), EXMeta::CacheCount - 1) : 0);
			const EXMeta::FCacheDef& Def = EXMeta::Cache(Kind);
			Title = Def.Name;
			static const TCHAR* Names[4] = { TEXT("Comum"), TEXT("Incomum"), TEXT("Raro"), TEXT("\u00C9pico") };
			for (int32 R = 0; R < 4; ++R)
			{
				if (Def.Odds[R] > 0.0f)
				{
					Line(TEXT("PROBABILIDADE"), FString::Printf(TEXT("%s  %d%%"), Names[R], FMath::RoundToInt(Def.Odds[R] * 100.0f)), FString(),
						EXMeta::RarityColour(static_cast<EEXRarity>(R)));
				}
			}
			Detail = FString::Printf(TEXT("%s. 4 a 6 m\u00F3dulos (5 a 6 na ELITE) e o resto consum\u00EDveis. Nunca traz naves.%s"), Def.Promise,
				bShop ? TEXT(" Enter compra; abre-se no COFRE.") : TEXT(" Enter abre."));
			return;
		}
		if (const FEXItem* Item = LookedItem())
		{
			Title = EXMeta::ItemLabel(*Item);
			for (int32 Stat = 0; Stat < EXMeta::StatCount; ++Stat)
			{
				const int32 V = Item->Roll(static_cast<EEXStat>(Stat));
				if (V != 0 && Stat != static_cast<int32>(EEXStat::Mass))
				{
					Line(EXMeta::StatName(static_cast<EEXStat>(Stat)).ToUpper(), FString::Printf(TEXT("%+d"), V), FString(),
						V > 0 ? FLinearColor(0.48f, 0.88f, 0.54f) : FLinearColor(1.0f, 0.35f, 0.29f));
				}
			}
			DescribeItem(*Item, Detail);
			Detail += bShop ? FString::Printf(TEXT("\nEnter compra por %s STARDUST."), *HangarDust(EXMeta::ShopPrice(*Item)))
				: FString::Printf(TEXT("\nValor %s \u00B7 vende por %s (Enter duas vezes)."), *HangarDust(Item->Value), *HangarDust(EXMeta::SellValue(*Item)));
		}
		else
		{
			Title = bShop ? FString(TEXT("LOJA")) : FString(TEXT("COFRE"));
			Detail = bShop ? FString(TEXT("A oferta muda depois de cada expedi\u00E7\u00E3o.")) : FString(TEXT("Ainda n\u00E3o tens m\u00F3dulos: abre uma caixa."));
		}
		return;
	}
	default:
		return;
	}
}

void UEXHangarModel::SellCommons()
{
	UEXProfileSave* Profile = GetProfile();
	if (!Profile || !bOpening)
	{
		return;
	}
	int32 Sold = 0;
	int32 Paid = 0;
	for (int32 Index = 0; Index < Cards.Num() && Index < CardSerials.Num(); ++Index)
	{
		const FEXItem* Item = CardSerials[Index] ? Profile->FindItem(CardSerials[Index]) : nullptr;
		if (!Item || Item->Rarity != static_cast<uint8>(EEXRarity::Common) || !Profile->EquippedOn(Item->Serial).IsEmpty())
		{
			continue;
		}
		Paid += EXMeta::SellValue(*Item);
		Profile->RemoveItem(Item->Serial);
		CardSerials[Index] = 0;
		Cards[Index].Tag = TEXT("VENDIDA");
		Cards[Index].bDim = true;
		++Sold;
	}
	if (Sold == 0)
	{
		Note(TEXT("Nada comum para vender nesta caixa"));
		return;
	}
	Profile->Stardust += Paid;
	CacheValue = FMath::Max(0, CacheValue);
	Note(FString::Printf(TEXT("Vendidas %d pe\u00E7as comuns: +%s STARDUST"), Sold, *HangarDust(Paid)));
	SaveProfile();
	Touch();
}

FString UEXHangarModel::GetPreviewLabel(FLinearColor& OutColour) const
{
	OutColour = EXUiHangarSand();
	if (CurrentTab != EEXHangarTab::Equip || bOpening)
	{
		return FString();
	}
	const UEXProfileSave* Profile = GetProfile();
	const FEXItem* Item = Profile ? Profile->FindItem(CandidateSerial()) : nullptr;
	if (Item)
	{
		OutColour = EXMeta::RarityColour(static_cast<EEXRarity>(Item->Rarity));
	}
	const EEXFamily Slot = CurrentSlot();
	if (Slot == EEXFamily::Engine || Slot == EEXFamily::Propulsion || Slot == EEXFamily::Reactor || Slot == EEXFamily::Utility)
	{
		return Slot == EEXFamily::Utility ? FString(TEXT("VISTA EM ESQUELETO  \u00B7  UTILIT\u00C1RIO NO NARIZ"))
			: FString(TEXT("VISTA EM ESQUELETO  \u00B7  MOTOR LIGADO"));
	}
	return Item ? FString::Printf(TEXT("PR\u00C9-VISUALIZA\u00C7\u00C3O  \u00B7  %s"), *EXMeta::ItemLabel(*Item).ToUpper())
		: FString::Printf(TEXT("DE S\u00C9RIE  \u00B7  %s"), *EXMeta::FamilyName(Slot));
}

TArray<FEXHangarCallout> UEXHangarModel::GetCallouts() const
{
	TArray<FEXHangarCallout> Out;
	if (CurrentTab != EEXHangarTab::Equip || bOpening)
	{
		return Out;
	}
	const TArray<FEXItem> Build = GetPreviewBuild();
	auto Add = [&Out](const FEXItem& Item, bool bWithRarity)
	{
		const EXMeta::FModuleDef* Def = EXMeta::Find(Item);
		if (!Def)
		{
			return;
		}
		FEXHangarCallout& Pin = Out.AddDefaulted_GetRef();
		Pin.Family = Def->Family;
		Pin.Colour = EXMeta::RarityColour(static_cast<EEXRarity>(Item.Rarity));
		Pin.Text = Def->Family == EEXFamily::Reactor ? FString::Printf(TEXT("reator  \u00B7  %s"), HangarLookOf(*Def, true)) : FString(HangarLookOf(*Def, true));
		if (bWithRarity && Def->Family == EEXFamily::Engine && Item.Rarity >= static_cast<uint8>(EEXRarity::Rare))
		{
			Pin.Text += Item.Rarity >= static_cast<uint8>(EEXRarity::Epic) ? TEXT(" (\u00E9pico)") : TEXT(" (mais longa)");
		}
	};
	const int32 Slot = static_cast<int32>(CurrentSlot());
	if (Build.IsValidIndex(Slot) && Build[Slot].IsValid())
	{
		Add(Build[Slot], true);
	}
	// The skeleton shows the reactor too: its glow is the reactor module's colour.
	const int32 Reactor = static_cast<int32>(EEXFamily::Reactor);
	const bool bXRay = CurrentSlot() == EEXFamily::Engine || CurrentSlot() == EEXFamily::Propulsion || CurrentSlot() == EEXFamily::Utility;
	if (bXRay && Build.IsValidIndex(Reactor))
	{
		if (Build[Reactor].IsValid())
		{
			Add(Build[Reactor], false);
		}
		else
		{
			FEXHangarCallout& Pin = Out.AddDefaulted_GetRef();
			Pin.Family = EEXFamily::Reactor;
			Pin.Colour = EXUiHangarSand();
			Pin.Text = TEXT("reator  \u00B7  brilha na cor do m\u00F3dulo");
		}
	}
	return Out;
}

bool UEXHangarModel::GetLookedCard(FEXHangarRow& OutCard) const
{
	const FEXItem* Item = LookedItem();
	if (!Item)
	{
		return false;
	}
	OutCard = ItemCard(*Item);
	if (CurrentTab == EEXHangarTab::Shop)
	{
		OutCard.Value = EXMeta::ShopPrice(*Item);
	}
	return true;
}

FString UEXHangarModel::GetQuickSummary() const
{
	const UEXProfileSave* Profile = GetProfile();
	int32 Carried = 0;
	for (int32 Slot = 0; Profile && Slot < Profile->Quick.Num(); ++Slot)
	{
		Carried += Profile->Quick[Slot].Count;
	}
	return FString::Printf(TEXT("Levas %d consum\u00EDveis  \u00B7  valor em risco %s STARDUST\nSe fores destru\u00EDdo, perdes os que levas. Se extra\u00EDres, os que n\u00E3o "
		"gastaste voltam ao stock."), Carried, *HangarDust(EXEconomy::QuickValue(Profile)));
}

TArray<FEXHangarHint> UEXHangarModel::GetHints() const
{
	TArray<FEXHangarHint> Hints;
	auto Add = [&Hints](std::initializer_list<const TCHAR*> Keys, const TCHAR* Label)
	{
		FEXHangarHint& Hint = Hints.AddDefaulted_GetRef();
		for (const TCHAR* Key : Keys)
		{
			Hint.Keys.Add(Key);
		}
		Hint.Label = Label;
	};
	if (bOpening)
	{
		if (Revealed < Cards.Num())
		{
			Add({ TEXT("Enter") }, TEXT("Revelar a pr\u00F3xima"));
			Add({ TEXT("Espa\u00E7o") }, TEXT("Revelar todas"));
		}
		else
		{
			Add({ TEXT("Enter") }, TEXT("Guardar tudo"));
			Add({ TEXT("\u232B") }, TEXT("Vender comuns (25%)"));
		}
		Add({ TEXT("Esc") }, TEXT("Fechar"));
		return Hints;
	}
	Add({ TEXT("Q"), TEXT("E") }, TEXT("Separadores"));
	switch (CurrentTab)
	{
	case EEXHangarTab::Ship:
		Add({ TEXT("W"), TEXT("S") }, TEXT("Nave"));
		Add({ TEXT("Enter") }, TEXT("Lan\u00E7ar expedi\u00E7\u00E3o"));
		Add({ TEXT("Rato") }, TEXT("Rodar"));
		Add({ TEXT("Roda") }, TEXT("Zoom"));
		break;
	case EEXHangarTab::Equip:
		Add({ TEXT("W"), TEXT("S") }, TEXT("Slot"));
		Add({ TEXT("A"), TEXT("D") }, TEXT("Pe\u00E7a"));
		Add({ TEXT("Enter") }, TEXT("Montar"));
		Add({ TEXT("\u232B") }, TEXT("De s\u00E9rie"));
		Add({ TEXT("T") }, TEXT("Segurar"));
		break;
	case EEXHangarTab::Quick:
		Add({ TEXT("W"), TEXT("S") }, TEXT("Slot"));
		Add({ TEXT("A"), TEXT("D") }, TEXT("Quantidade (compra o que faltar)"));
		Add({ TEXT("Enter") }, TEXT("Trocar consum\u00EDvel"));
		Add({ TEXT("\u232B") }, TEXT("Esvaziar"));
		break;
	case EEXHangarTab::Shop:
		Add({ TEXT("W"), TEXT("S") }, TEXT("Item"));
		Add({ TEXT("Enter") }, TEXT("Comprar"));
		break;
	case EEXHangarTab::Vault:
		Add({ TEXT("W"), TEXT("S") }, TEXT("Item"));
		Add({ TEXT("Enter") }, TEXT("Abrir caixa / vender"));
		break;
	default:
		break;
	}
	Add({ TEXT("Esc") }, TEXT("Menu"));
	return Hints;
}
