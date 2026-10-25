#include "Game/EXMeta.h"

namespace EXMeta
{
namespace
{
	// Budget and average value by rarity (doc 02 sec. 7, doc 03 sec. 10).
	constexpr int32 RarityBudget[RarityCount] = { 10, 13, 16, 20, 23 };
	constexpr int32 RarityValue[RarityCount] = { 500, 1100, 3000, 7000, 18000 };

	// Lives as in the prototype (Docs/MODOS_DE_JOGO.md); stats, mass and slots from doc 02 sec. 4 (the old chassis).
	const FShipDef Ships[] = {
		{ TEXT("STRIX"), { 72, 74, 76, 75, 66, 66, 68, 70 }, 1450, 3, { SizeM, SizeM, SizeAny, SizeM, SizeM, SizeM, SizeM, SizeAny },
			TEXT("ADAPTIVE TRIM"), TEXT("Depois de aterrar ou sair de uma parede, recupera a estabilidade mais depressa.") },
		{ TEXT("WRAITH"), { 82, 80, 90, 58, 46, 57, 60, 78 }, 1180, 3, { SizeS | SizeM, SizeS, SizeAny, SizeS, SizeS, SizeS | SizeM, SizeS, SizeAny },
			TEXT("RAZOR LINE"), TEXT("Deitada em curva sem tocar em nada, corta o ar: menos arrasto enquanto mantiver a linha.") },
		{ TEXT("NOMAD"), { 65, 63, 62, 77, 76, 92, 84, 60 }, 1650, 4, { SizeM | SizeL, SizeM, SizeAny, SizeM | SizeL, SizeM, SizeM | SizeL, SizeL, SizeAny },
			TEXT("LONG HAUL"), TEXT("Fria durante muito tempo, fica mais eficiente.") },
		{ TEXT("BASTION"), { 61, 54, 52, 92, 96, 65, 73, 55 }, 1950, 5, { SizeL, SizeL, 0, SizeL, SizeL, SizeL, SizeL, SizeAny },
			TEXT("INERTIAL ANCHOR"), TEXT("Os toques e a turbul\u00EAncia desviam-na menos.") },
		{ TEXT("VORTEX"), { 75, 91, 68, 65, 61, 49, 55, 96 }, 1500, 2, { SizeM, SizeS | SizeM, SizeAny, SizeM, SizeS | SizeM, SizeM, SizeM, SizeAny },
			TEXT("OVERDRIVE RECOVERY"), TEXT("Depois de um nitro longo, arrefece e recupera mais depressa.") },
	};

	const FConsumableDef Consumables[] = {
		{ TEXT("none"), TEXT("Vazio"), TEXT(""), 0, FLinearColor(0.4f, 0.4f, 0.4f) },
		{ TEXT("coolant"), TEXT("Coolant Cell"), TEXT("-45 de calor"), 80, FLinearColor(0.42f, 0.82f, 1.0f) },
		{ TEXT("foam"), TEXT("Repair Foam"), TEXT("+1 vida em 8 s; -10% de velocidade enquanto repara"), 100, FLinearColor(0.48f, 0.88f, 0.54f) },
		{ TEXT("fuel"), TEXT("Fuel Cell"), TEXT("+30% de combust\u00EDvel"), 120, FLinearColor(1.0f, 0.71f, 0.28f) },
		{ TEXT("stab"), TEXT("Stabilizer Shot"), TEXT("8 s de ader\u00EAncia e estabilidade extra"), 140, FLinearColor(0.79f, 0.61f, 1.0f) },
		{ TEXT("surge"), TEXT("Surge Cell"), TEXT("+70% de nitro na hora; +12 de calor"), 180, FLinearColor(1.0f, 0.83f, 0.29f) },
		{ TEXT("nanogel"), TEXT("Rapid Nanogel"), TEXT("+1 vida em 2,5 s; -25% de velocidade enquanto repara"), 220, FLinearColor(0.24f, 1.0f, 0.6f) },
	};

	// The ELITE costs 10 000 in the demo (doc 03 plans 13 500 for the full game).
	const FCacheDef Caches[] = {
		{ TEXT("STANDARD CACHE"), 2500, { 0.70f, 0.27f, 0.03f, 0.0f }, TEXT("10 itens \u00B7 70% comuns, 27% incomuns, 3% raros") },
		{ TEXT("ADVANCED CACHE"), 6000, { 0.20f, 0.50f, 0.27f, 0.03f }, TEXT("10 itens \u00B7 m\u00EDnimo 1 raro \u00B7 3% \u00E9picos") },
		{ TEXT("ELITE CACHE"), 10000, { 0.0f, 0.25f, 0.55f, 0.20f }, TEXT("10 itens \u00B7 1 \u00E9pico garantido \u00B7 4 raros ou melhor \u00B7 4% lend\u00E1rio") },
	};

	// Flame styles: stock, sprint, endurance, burner, razor, heavy, relic, redline.
	enum EFlame : int32 { FlameStock, FlameSprint, FlameEndurance, FlameBurner, FlameRazor, FlameHeavy, FlameRelic, FlameRedline };
	const FFlameStyle Flames[] = {
		{ FLinearColor(1.0f, 0.30f, 0.06f), FLinearColor(1.0f, 0.72f, 0.38f), 1.0f, 1.0f, 0, false },
		{ FLinearColor(0.20f, 0.45f, 1.0f), FLinearColor(0.85f, 0.95f, 1.0f), 1.45f, 0.85f, 0, false },
		{ FLinearColor(0.10f, 0.80f, 1.0f), FLinearColor(0.70f, 1.0f, 1.0f), 0.75f, 1.1f, 0, false },
		{ FLinearColor(1.0f, 0.55f, 0.12f), FLinearColor(1.0f, 0.95f, 0.70f), 1.55f, 1.0f, 3, false },
		{ FLinearColor(0.55f, 0.25f, 1.0f), FLinearColor(0.92f, 0.85f, 1.0f), 1.4f, 0.6f, 0, false },
		{ FLinearColor(1.0f, 0.25f, 0.05f), FLinearColor(1.0f, 0.60f, 0.25f), 0.95f, 1.35f, 0, false },
		{ FLinearColor(0.35f, 0.60f, 1.0f), FLinearColor(1.0f, 1.0f, 1.0f), 2.1f, 0.45f, 0, false },
		{ FLinearColor(1.0f, 0.08f, 0.06f), FLinearColor(1.0f, 0.85f, 0.80f), 1.7f, 0.9f, 4, true },
	};
	const FLinearColor ReactorColours[] = {
		FLinearColor(1.0f, 0.54f, 0.24f),   // stock
		FLinearColor(0.25f, 0.95f, 1.0f),   // spark: cyan
		FLinearColor(0.25f, 0.45f, 1.0f),   // steady: blue
		FLinearColor(1.0f, 0.25f, 0.85f),   // flux: magenta
		FLinearColor(1.0f, 0.62f, 0.12f),   // titan: amber
		FLinearColor(1.0f, 0.88f, 0.50f),   // helios: pale gold
	};
	const FLinearColor NitroColours[] = {
		FLinearColor(0.25f, 0.45f, 1.0f),   // stock
		FLinearColor(0.30f, 0.90f, 1.0f),   // twin jets: cyan
		FLinearColor(0.35f, 0.40f, 1.0f),   // vector: deep blue
		FLinearColor(0.75f, 0.45f, 1.0f),   // heavy thrust: violet
	};

	FStatRule Rule(EEXStat Stat, int32 Cap, float Weight = 1.0f)
	{
		return FStatRule{ Stat, Cap, Weight };
	}

	// What each family may give, with its ceiling per item (doc 02 sec. 6-7), and the stats that may pay for it.
	TArray<FStatRule> FamilyStats(EEXFamily Family)
	{
		switch (Family)
		{
		case EEXFamily::Engine: return { Rule(EEXStat::Speed, 9), Rule(EEXStat::Accel, 8), Rule(EEXStat::Efficiency, 6) };
		case EEXFamily::Propulsion: return { Rule(EEXStat::Boost, 9), Rule(EEXStat::Accel, 7), Rule(EEXStat::Efficiency, 4) };
		case EEXFamily::Wings: return { Rule(EEXStat::Handling, 9), Rule(EEXStat::Stability, 9) };
		case EEXFamily::Tail: return { Rule(EEXStat::Handling, 6), Rule(EEXStat::Stability, 7), Rule(EEXStat::Cooling, 5) };
		case EEXFamily::Armor: return { Rule(EEXStat::Hull, 14), Rule(EEXStat::Cooling, 4) };
		case EEXFamily::Reactor: return { Rule(EEXStat::Boost, 10), Rule(EEXStat::Efficiency, 4) };
		case EEXFamily::Cooling: return { Rule(EEXStat::Cooling, 12), Rule(EEXStat::Repair, 8) };
		default: return { Rule(EEXStat::Intel, 10), Rule(EEXStat::Repair, 5), Rule(EEXStat::Efficiency, 3) };
		}
	}

	TArray<FStatRule> FamilyDrawbacks(EEXFamily Family)
	{
		switch (Family)
		{
		case EEXFamily::Engine: return { Rule(EEXStat::Efficiency, 6), Rule(EEXStat::Cooling, 6) };
		case EEXFamily::Propulsion: return { Rule(EEXStat::Cooling, 6), Rule(EEXStat::Efficiency, 5) };
		case EEXFamily::Wings: return { Rule(EEXStat::Speed, 3), Rule(EEXStat::Accel, 3) };
		case EEXFamily::Tail: return { Rule(EEXStat::Speed, 2) };
		case EEXFamily::Armor: return { Rule(EEXStat::Accel, 6), Rule(EEXStat::Handling, 4) };
		case EEXFamily::Reactor: return { Rule(EEXStat::Cooling, 6) };
		case EEXFamily::Cooling: return { Rule(EEXStat::Accel, 3) };
		default: return {};
		}
	}

	/** A stat the model favours when it spends a module's budget. */
	struct FPrefer
	{
		EEXStat Stat;
		float Weight;
	};

	FModuleDef Module(const TCHAR* Id, const TCHAR* Name, const TCHAR* Maker, EEXFamily Family, uint8 Size, int32 MassKg,
		const TCHAR* Piece, int32 Look, const TCHAR* Description, std::initializer_list<FPrefer> Prefer)
	{
		FModuleDef Def;
		Def.Id = FName(Id);
		Def.Name = Name;
		Def.Maker = Maker;
		Def.Description = Description;
		Def.Family = Family;
		Def.Size = Size;
		Def.MassKg = MassKg;
		Def.Piece = Piece;
		Def.Look = Look;
		Def.Stats = FamilyStats(Family);
		for (FStatRule& R : Def.Stats)
		{
			for (const FPrefer& P : Prefer)
			{
				if (P.Stat == R.Stat)
				{
					R.Weight = P.Weight;
				}
			}
		}
		Def.Drawbacks = FamilyDrawbacks(Family);
		return Def;
	}

	FModuleDef Legendary(const TCHAR* Id, const TCHAR* Name, const TCHAR* Maker, EEXFamily Family, int32 MassKg, const TCHAR* Piece,
		int32 Look, const TCHAR* Perk, const TCHAR* PerkText, const TCHAR* Prefix, std::initializer_list<FStatRoll> Rolls)
	{
		FModuleDef Def = Module(Id, Name, Maker, Family, SizeM, MassKg, Piece, Look, PerkText, {});
		Def.bLegendary = true;
		Def.Perk = Perk;
		Def.PerkText = PerkText;
		Def.SerialPrefix = Prefix;
		Def.FixedRolls.Append(Rolls.begin(), static_cast<int32>(Rolls.size()));
		return Def;
	}

	const TArray<FModuleDef>& Catalogue()
	{
		static TArray<FModuleDef> List;
		if (List.Num() > 0)
		{
			return List;
		}
		using S = EEXStat;
		using F = EEXFamily;
		// Engines (6): inside the hull, each with its own flame.
		List.Add(Module(TEXT("eng_vk4"), TEXT("APEX VK-4 Sprint"), TEXT("APEX Dynamics"), F::Engine, SizeM, 0, TEXT(""), FlameSprint,
			TEXT("Motor de competi\u00E7\u00E3o: velocidade de ponta."), { { S::Speed, 3.0f } }));
		List.Add(Module(TEXT("eng_longstride"), TEXT("Meridian Longstride"), TEXT("Meridian Engineering"), F::Engine, SizeM, 20, TEXT(""), FlameEndurance,
			TEXT("Consumo baixo para expedi\u00E7\u00F5es longas."), { { S::Efficiency, 3.0f } }));
		List.Add(Module(TEXT("eng_hx"), TEXT("Vanta HX Burner"), TEXT("Vanta Works"), F::Engine, SizeS, -10, TEXT(""), FlameBurner,
			TEXT("Compacto e explosivo \u00E0 sa\u00EDda das curvas."), { { S::Accel, 3.0f } }));
		List.Add(Module(TEXT("eng_razor"), TEXT("APEX Razor-S"), TEXT("APEX Dynamics"), F::Engine, SizeS, -20, TEXT(""), FlameRazor,
			TEXT("Motor leve para chassis estreitos."), { { S::Speed, 2.0f }, { S::Accel, 1.5f } }));
		List.Add(Module(TEXT("eng_ironcore"), TEXT("Frontier Ironcore"), TEXT("Frontier Systems"), F::Engine, SizeL, 70, TEXT(""), FlameHeavy,
			TEXT("Bloco pesado, pot\u00EAncia est\u00E1vel."), { { S::Accel, 2.0f }, { S::Speed, 1.5f } }));
		List.Add(Module(TEXT("eng_relic"), TEXT("Oryx Relic Drive"), TEXT("Oryx Reclamation"), F::Engine, SizeL, 40, TEXT(""), FlameRelic,
			TEXT("Tecnologia recuperada: r\u00E1pida e frugal."), { { S::Speed, 2.0f }, { S::Efficiency, 2.0f } }));
		// Propulsion (3): the nitro.
		List.Add(Module(TEXT("prop_twin"), TEXT("APEX Twin Jets"), TEXT("APEX Dynamics"), F::Propulsion, SizeS, -5, TEXT(""), 1,
			TEXT("Impulso afiado, pouca massa."), { { S::Boost, 2.5f } }));
		List.Add(Module(TEXT("prop_vector"), TEXT("Meridian Vector M"), TEXT("Meridian Engineering"), F::Propulsion, SizeM, 15, TEXT(""), 2,
			TEXT("Vectoring para a sa\u00EDda das curvas."), { { S::Accel, 2.0f } }));
		List.Add(Module(TEXT("prop_heavy"), TEXT("Frontier Heavy Thrust"), TEXT("Frontier Systems"), F::Propulsion, SizeL, 60, TEXT(""), 3,
			TEXT("Propulsores grandes: for\u00E7a bruta."), { { S::Boost, 2.0f }, { S::Accel, 1.5f } }));
		// Wings (3 per ship): grown from the ship's own wing, so they belong to it. The five kinds of the old catalogue.
		struct FWingKind { const TCHAR* Key; const TCHAR* Label; const TCHAR* Maker; uint8 Size; int32 Mass; const TCHAR* Text; float Handling, Stability; };
		const FWingKind Kinds[] = {
			{ TEXT("blade"), TEXT("Blade"), TEXT("APEX Dynamics"), SizeS, -10, TEXT("Curta e enflechada, com barbatana na ponta: agilidade."), 3.0f, 1.0f },
			{ TEXT("longspan"), TEXT("Longspan"), TEXT("Meridian Engineering"), SizeM, 25, TEXT("Longa, com placas na ponta: curvas deitadas e aterragens."), 1.0f, 3.0f },
			{ TEXT("vector"), TEXT("Vector"), TEXT("Vanta Works"), SizeM, 5, TEXT("Segunda superf\u00EDcie por cima: manobra e estabilidade."), 2.0f, 1.5f },
			{ TEXT("brace"), TEXT("Brace"), TEXT("Frontier Systems"), SizeL, 50, TEXT("Grossa, com escora at\u00E9 ao casco: aguenta as paredes."), 1.0f, 3.0f },
			{ TEXT("glide"), TEXT("Glide"), TEXT("Oryx Reclamation"), SizeL, 30, TEXT("Ponta dobrada e bordo de ataque luminoso: controlo no ar."), 2.0f, 2.0f },
		};
		struct FShipWings { const TCHAR* Ship; const TCHAR* Kinds[3]; };
		const FShipWings ShipWings[] = {
			{ TEXT("STRIX"), { TEXT("blade"), TEXT("longspan"), TEXT("vector") } },
			{ TEXT("WRAITH"), { TEXT("blade"), TEXT("vector"), TEXT("glide") } },
			{ TEXT("NOMAD"), { TEXT("longspan"), TEXT("brace"), TEXT("glide") } },
			{ TEXT("VORTEX"), { TEXT("blade"), TEXT("vector"), TEXT("glide") } },
		};
		for (const FShipWings& SW : ShipWings)
		{
			for (const TCHAR* Key : SW.Kinds)
			{
				for (const FWingKind& K : Kinds)
				{
					if (FCString::Strcmp(K.Key, Key) != 0)
					{
						continue;
					}
					const FString ShipName(SW.Ship);
					FModuleDef Def = Module(*FString::Printf(TEXT("wing_%s_%s"), K.Key, *ShipName.ToLower()), *FString::Printf(TEXT("%s %s"), *ShipName, K.Label),
						K.Maker, F::Wings, SizeAny, K.Mass, *FString::Printf(TEXT("wing_%s"), K.Key), 0, K.Text,
						{ { S::Handling, K.Handling }, { S::Stability, K.Stability } });
					Def.Ship = ShipName;
					List.Add(Def);
				}
			}
		}
		// Armour (4).
		List.Add(Module(TEXT("arm_skin"), TEXT("APEX Light Skin"), TEXT("APEX Dynamics"), F::Armor, SizeS, 30, TEXT("armor_light"), 0,
			TEXT("Prote\u00E7\u00E3o m\u00EDnima, quase sem massa."), { { S::Hull, 2.0f } }));
		List.Add(Module(TEXT("arm_guard"), TEXT("Meridian Guard Plates"), TEXT("Meridian Engineering"), F::Armor, SizeM, 90, TEXT("armor_guard"), 0,
			TEXT("Placas modulares f\u00E1ceis de reparar."), { { S::Hull, 3.0f } }));
		List.Add(Module(TEXT("arm_plate"), TEXT("Frontier Bulwark"), TEXT("Frontier Systems"), F::Armor, SizeL, 180, TEXT("armor_bulwark"), 0,
			TEXT("Pain\u00E9is grossos e absorvedores."), { { S::Hull, 4.0f } }));
		List.Add(Module(TEXT("arm_shell"), TEXT("Oryx Shell Lattice"), TEXT("Oryx Reclamation"), F::Armor, SizeM, 70, TEXT("armor_shell"), 0,
			TEXT("Carapa\u00E7a recuperada com resist\u00EAncia t\u00E9rmica."), { { S::Hull, 2.0f }, { S::Cooling, 1.5f } }));
		// Reactors (4): inside the hull, each with its glow.
		List.Add(Module(TEXT("rea_spark"), TEXT("APEX Spark Core"), TEXT("APEX Dynamics"), F::Reactor, SizeS, 0, TEXT(""), 1,
			TEXT("Recarga r\u00E1pida de energia."), { { S::Boost, 3.0f } }));
		List.Add(Module(TEXT("rea_steady"), TEXT("Meridian Steady Core"), TEXT("Meridian Engineering"), F::Reactor, SizeM, 20, TEXT(""), 2,
			TEXT("Energia est\u00E1vel e eficiente."), { { S::Efficiency, 2.0f } }));
		List.Add(Module(TEXT("rea_flux"), TEXT("Vanta Flux Reactor"), TEXT("Vanta Works"), F::Reactor, SizeM, 15, TEXT(""), 3,
			TEXT("Muita energia, muito calor."), { { S::Boost, 3.0f } }));
		List.Add(Module(TEXT("rea_titan"), TEXT("Frontier Titan Core"), TEXT("Frontier Systems"), F::Reactor, SizeL, 60, TEXT(""), 4,
			TEXT("Reator pesado de grande capacidade."), { { S::Boost, 2.0f } }));
		// Cooling (3).
		List.Add(Module(TEXT("cool_vent"), TEXT("APEX Vent Kit"), TEXT("APEX Dynamics"), F::Cooling, SizeS, 10, TEXT("cooling_vents"), 0,
			TEXT("Grelhas compactas."), { { S::Cooling, 3.0f } }));
		List.Add(Module(TEXT("cool_radiator"), TEXT("Meridian Radiator Array"), TEXT("Meridian Engineering"), F::Cooling, SizeM, 35, TEXT("cooling_radiator"), 0,
			TEXT("Radiadores grandes e apoio \u00E0s repara\u00E7\u00F5es."), { { S::Repair, 2.0f } }));
		List.Add(Module(TEXT("cool_grid"), TEXT("Frontier Heat Grid"), TEXT("Frontier Systems"), F::Cooling, SizeL, 70, TEXT("cooling_grid"), 0,
			TEXT("Grelhas t\u00E9rmicas pesadas."), { { S::Cooling, 3.0f } }));
		// Tails (3).
		List.Add(Module(TEXT("tail_compact"), TEXT("APEX Compact Tail"), TEXT("APEX Dynamics"), F::Tail, SizeS, 0, TEXT("tail_compact"), 0,
			TEXT("Cauda curta: vira mais depressa."), { { S::Handling, 3.0f } }));
		List.Add(Module(TEXT("tail_twin"), TEXT("Meridian Twin Tail"), TEXT("Meridian Engineering"), F::Tail, SizeM, 20, TEXT("tail_twin"), 0,
			TEXT("Cauda dupla est\u00E1vel."), { { S::Stability, 3.0f } }));
		List.Add(Module(TEXT("tail_long"), TEXT("Frontier Long Keel"), TEXT("Frontier Systems"), F::Tail, SizeL, 40, TEXT("tail_keel"), 0,
			TEXT("Quilha longa com grelhas."), { { S::Stability, 2.0f }, { S::Cooling, 2.0f } }));
		// Utility (3).
		List.Add(Module(TEXT("util_scanner"), TEXT("Meridian Scanner Mast"), TEXT("Meridian Engineering"), F::Utility, SizeM, 8, TEXT("utility_mast"), 0,
			TEXT("Avisos de perigo mais cedo."), { { S::Intel, 3.0f } }));
		List.Add(Module(TEXT("util_routeintel"), TEXT("Oryx Route Oracle"), TEXT("Oryx Reclamation"), F::Utility, SizeM, 5, TEXT("utility_dome"), 0,
			TEXT("L\u00EA as rotas e os rivais."), { { S::Intel, 2.0f }, { S::Efficiency, 1.5f } }));
		List.Add(Module(TEXT("util_drone"), TEXT("Frontier Field Drone"), TEXT("Frontier Systems"), F::Utility, SizeM, 15, TEXT("utility_drone"), 0,
			TEXT("Apoio \u00E0s repara\u00E7\u00F5es em corrida."), { { S::Repair, 3.0f } }));
		// Legendaries (doc 02 sec. 8).
		List.Add(Legendary(TEXT("leg_helios"), TEXT("HELIOS V-9"), TEXT("Vanta Works"), F::Reactor, 20, TEXT(""), 5, TEXT("helios"),
			TEXT("Energia +17% \u00B7 nitro +11% \u00B7 refrigera\u00E7\u00E3o +8 \u00B7 combust\u00EDvel +6%"), TEXT("HV9"),
			{ { S::Boost, 14 }, { S::Cooling, 8 }, { S::Efficiency, -6 } }));
		List.Add(Legendary(TEXT("leg_redline"), TEXT("REDLINE-X"), TEXT("APEX Dynamics"), F::Engine, 10, TEXT(""), FlameRedline, TEXT("redline"),
			TEXT("Acima de 90% da velocidade m\u00E1xima: +3% de velocidade \u00B7 calor do nitro +15%"), TEXT("RLX"),
			{ { S::Speed, 13 }, { S::Accel, 9 }, { S::Cooling, -5 } }));
		List.Add(Legendary(TEXT("leg_aegis"), TEXT("AEGIS FRAME"), TEXT("Frontier Systems"), F::Armor, 120, TEXT("armor_aegis"), 0, TEXT("aegis"),
			TEXT("Choques -25% \u00B7 massa +120 kg"), TEXT("AEG"),
			{ { S::Hull, 20 }, { S::Cooling, 4 }, { S::Accel, -4 } }));
		return List;
	}

	int32 Weighted(FRandomStream& Random, const TArray<float>& Weights)
	{
		float Sum = 0.0f;
		for (const float W : Weights)
		{
			Sum += FMath::Max(0.0f, W);
		}
		if (Sum <= 0.0f)
		{
			return 0;
		}
		float Pick = Random.FRand() * Sum;
		for (int32 Index = 0; Index < Weights.Num(); ++Index)
		{
			Pick -= FMath::Max(0.0f, Weights[Index]);
			if (Pick < 0.0f)
			{
				return Index;
			}
		}
		return Weights.Num() - 1;
	}

	int32 Round10(float Value, int32 Step = 10)
	{
		return FMath::RoundToInt(Value / Step) * Step;
	}

	TArray<const FModuleDef*> Regular(EEXFamily Family)
	{
		TArray<const FModuleDef*> Out;
		for (const FModuleDef& Def : Catalogue())
		{
			if (!Def.bLegendary && Def.Family == Family)
			{
				Out.Add(&Def);
			}
		}
		return Out;
	}

	int32 FlameIndex(const FEXItem* Engine)
	{
		const FModuleDef* Def = Engine ? EXMeta::Find(*Engine) : nullptr;
		return Def ? FMath::Clamp(Def->Look, 0, static_cast<int32>(UE_ARRAY_COUNT(Flames)) - 1) : FlameStock;
	}
}

	int32 ModuleCount()
	{
		return Catalogue().Num();
	}

	const FModuleDef& ModuleAt(int32 Index)
	{
		return Catalogue()[FMath::Clamp(Index, 0, Catalogue().Num() - 1)];
	}

	const FModuleDef* Find(FName Id)
	{
		if (Id.IsNone())
		{
			return nullptr;
		}
		for (const FModuleDef& Def : Catalogue())
		{
			if (Def.Id == Id)
			{
				return &Def;
			}
		}
		return nullptr;
	}

	const FModuleDef* Find(const FEXItem& Item)
	{
		return Find(Item.Def);
	}

	const FShipDef& Ship(const FString& Name)
	{
		for (const FShipDef& Def : Ships)
		{
			if (Name.Equals(Def.Name, ESearchCase::IgnoreCase))
			{
				return Def;
			}
		}
		return Ships[0];
	}

	const FConsumableDef& Consumable(EEXConsumable Kind)
	{
		return Consumables[FMath::Clamp(static_cast<int32>(Kind), 0, ConsumableCount - 1)];
	}

	const FCacheDef& Cache(EEXCache Kind)
	{
		return Caches[FMath::Clamp(static_cast<int32>(Kind), 0, CacheCount - 1)];
	}

	FString FamilyName(EEXFamily Family)
	{
		static const TCHAR* Names[] = { TEXT("MOTOR"), TEXT("PROPULS\u00C3O"), TEXT("ASAS"), TEXT("CAUDA"), TEXT("BLINDAGEM"), TEXT("REATOR"),
			TEXT("REFRIGERA\u00C7\u00C3O"), TEXT("UTILIDADE") };
		return Names[FMath::Clamp(static_cast<int32>(Family), 0, FamilyCount - 1)];
	}

	FString StatName(EEXStat Stat)
	{
		static const TCHAR* Names[] = { TEXT("Velocidade"), TEXT("Acelera\u00E7\u00E3o"), TEXT("Manobra"), TEXT("Estabilidade"), TEXT("Casco"),
			TEXT("Efici\u00EAncia"), TEXT("Refrigera\u00E7\u00E3o"), TEXT("Nitro"), TEXT("Massa"), TEXT("Repara\u00E7\u00E3o"), TEXT("Sensores") };
		return Names[FMath::Clamp(static_cast<int32>(Stat), 0, StatCount - 1)];
	}

	FString StatShort(EEXStat Stat)
	{
		static const TCHAR* Names[] = { TEXT("VEL"), TEXT("ACE"), TEXT("MAN"), TEXT("EST"), TEXT("CAS"), TEXT("EFI"), TEXT("REF"), TEXT("NIT"),
			TEXT("kg"), TEXT("REP"), TEXT("SEN") };
		return Names[FMath::Clamp(static_cast<int32>(Stat), 0, StatCount - 1)];
	}

	FString RarityName(EEXRarity Rarity)
	{
		static const TCHAR* Names[] = { TEXT("COMUM"), TEXT("INCOMUM"), TEXT("RARO"), TEXT("\u00C9PICO"), TEXT("LEND\u00C1RIO") };
		return Names[FMath::Clamp(static_cast<int32>(Rarity), 0, RarityCount - 1)];
	}

	FLinearColor RarityColour(EEXRarity Rarity)
	{
		// White, green, blue, purple, gold (doc 02 sec. 7).
		static const FColor Colours[] = { FColor(0xE6, 0xE6, 0xE6), FColor(0x5C, 0xD3, 0x6B), FColor(0x4C, 0x9D, 0xFF), FColor(0xB4, 0x6B, 0xFF),
			FColor(0xFF, 0xC2, 0x3A) };
		return FLinearColor(Colours[FMath::Clamp(static_cast<int32>(Rarity), 0, RarityCount - 1)]);
	}

	FString SizeText(uint8 Sizes)
	{
		if (Sizes == SizeAny)
		{
			return TEXT("S/M/L");
		}
		FString Out;
		const TCHAR* Letters[] = { TEXT("S"), TEXT("M"), TEXT("L") };
		for (int32 Bit = 0; Bit < 3; ++Bit)
		{
			if (Sizes & (1 << Bit))
			{
				Out += Out.IsEmpty() ? Letters[Bit] : *FString::Printf(TEXT("/%s"), Letters[Bit]);
			}
		}
		return Out.IsEmpty() ? FString(TEXT("\u2014")) : Out;
	}

	FString ItemLabel(const FEXItem& Item)
	{
		const FModuleDef* Def = Find(Item);
		if (!Def)
		{
			return TEXT("De s\u00E9rie");
		}
		return Def->bLegendary ? FString::Printf(TEXT("%s %s-%04d"), *Def->Name, *Def->SerialPrefix, Item.Serial % 10000) : Def->Name;
	}

	FString RollText(const FEXItem& Item)
	{
		TArray<TPair<int32, int32>> Parts;
		for (int32 Stat = 0; Stat < Item.Rolls.Num() && Stat < StatCount; ++Stat)
		{
			if (Stat != static_cast<int32>(EEXStat::Mass) && Item.Rolls[Stat] != 0)
			{
				Parts.Add(TPair<int32, int32>(Stat, Item.Rolls[Stat]));
			}
		}
		Parts.Sort([](const TPair<int32, int32>& A, const TPair<int32, int32>& B) { return A.Value > B.Value; });
		FString Out;
		for (const TPair<int32, int32>& P : Parts)
		{
			Out += FString::Printf(TEXT("%s%s%d %s"), Out.IsEmpty() ? TEXT("") : TEXT("  "), P.Value > 0 ? TEXT("+") : TEXT(""), P.Value,
				*StatShort(static_cast<EEXStat>(P.Key)));
		}
		return Out;
	}

	int32 SellValue(const FEXItem& Item)
	{
		return FMath::Max(10, Round10(Item.Value * 0.25f));
	}

	int32 ShopPrice(const FEXItem& Item)
	{
		switch (static_cast<EEXRarity>(Item.Rarity))
		{
		case EEXRarity::Common: return Round10(FMath::Clamp(Item.Value, 450, 650));
		case EEXRarity::Uncommon: return Round10(FMath::Clamp(Item.Value, 900, 1300));
		case EEXRarity::Rare: return Round10(FMath::Clamp(Item.Value, 2400, 3500));
		default: return 0;
		}
	}

	bool Fits(const FModuleDef& Def, const FString& ShipName, EEXFamily Slot)
	{
		if (Def.Family != Slot)
		{
			return false;
		}
		if (!Def.Ship.IsEmpty() && !Def.Ship.Equals(ShipName, ESearchCase::IgnoreCase))
		{
			return false;
		}
		const uint8 Takes = Ship(ShipName).Sizes[static_cast<int32>(Slot)];
		return (Takes & Def.Size) != 0;
	}

	FEXItem Roll(const FModuleDef& Def, EEXRarity Rarity, FRandomStream& Random, int32 Serial)
	{
		FEXItem Item;
		Item.Def = Def.Id;
		Item.Serial = Serial;
		Item.Rolls.Init(0, StatCount);
		if (Def.bLegendary)
		{
			Rarity = EEXRarity::Legendary;
			for (const FStatRoll& R : Def.FixedRolls)
			{
				// Controlled rolls: a point either way on the gains keeps the piece's identity.
				Item.Rolls[static_cast<int32>(R.Stat)] += R.Value + (R.Value > 0 ? Random.RandRange(-1, 1) : 0);
			}
		}
		else
		{
			Rarity = static_cast<EEXRarity>(FMath::Min(static_cast<int32>(Rarity), static_cast<int32>(EEXRarity::Epic)));
			int32 Budget = RarityBudget[static_cast<int32>(Rarity)];
			// A drawback is likelier the rarer the piece (a specialist with a cost); it returns budget 1:1.
			static const float DrawChance[] = { 0.0f, 0.15f, 0.35f, 0.6f };
			if (Def.Drawbacks.Num() > 0 && Random.FRand() < DrawChance[static_cast<int32>(Rarity)])
			{
				const FStatRule& D = Def.Drawbacks[Random.RandRange(0, Def.Drawbacks.Num() - 1)];
				const int32 Pay = Random.RandRange(2, D.Cap);
				Item.Rolls[static_cast<int32>(D.Stat)] -= Pay;
				Budget += Pay;
			}
			TArray<float> Weights;
			for (int32 Point = 0; Point < Budget; ++Point)
			{
				Weights.Reset();
				float Sum = 0.0f;
				for (const FStatRule& R : Def.Stats)
				{
					const float W = Item.Rolls[static_cast<int32>(R.Stat)] >= R.Cap ? 0.0f : R.Weight;
					Weights.Add(W);
					Sum += W;
				}
				if (Sum <= 0.0f)
				{
					break;   // the family's ceilings are spent: the rest is lost
				}
				Item.Rolls[static_cast<int32>(Def.Stats[Weighted(Random, Weights)].Stat)] += 1;
			}
		}
		Item.Rolls[static_cast<int32>(EEXStat::Mass)] = FMath::RoundToInt(Def.MassKg * (1.0f + Random.FRandRange(-0.1f, 0.1f)));
		Item.Rarity = static_cast<uint8>(Rarity);
		// Valuation: the rarity's average times the quality of the rolls (0.9-1.15); legendaries 1.0-1.25.
		const float Average = RarityValue[static_cast<int32>(Rarity)];
		if (Rarity == EEXRarity::Legendary)
		{
			Item.Value = Round10(Average * Random.FRandRange(1.0f, 1.25f), 100);
		}
		else
		{
			int32 Spent = 0;
			for (int32 Stat = 0; Stat < StatCount; ++Stat)
			{
				if (Stat != static_cast<int32>(EEXStat::Mass) && Item.Rolls[Stat] > 0)
				{
					Spent += Item.Rolls[Stat];
				}
			}
			const float Quality = FMath::Min(1.0f, Spent / static_cast<float>(FMath::Max(1, RarityBudget[static_cast<int32>(Rarity)])));
			Item.Value = Round10(Average * (0.9f + 0.25f * Quality) * Random.FRandRange(0.95f, 1.05f));
		}
		return Item;
	}

	void Resolve(const FString& ShipName, const TArray<const FEXItem*>& Modules, int32 (&Out)[StatCount])
	{
		const FShipDef& Def = Ship(ShipName);
		for (int32 Stat = 0; Stat < StatCount; ++Stat)
		{
			Out[Stat] = Stat < CoreStats ? Def.Stats[Stat] : 0;
		}
		for (const FEXItem* Item : Modules)
		{
			if (!Item || !Item->IsValid())
			{
				continue;
			}
			for (int32 Stat = 0; Stat < StatCount && Stat < Item->Rolls.Num(); ++Stat)
			{
				Out[Stat] += Item->Rolls[Stat];
			}
		}
		for (int32 Stat = 0; Stat < CoreStats; ++Stat)
		{
			Out[Stat] = FMath::Clamp(Out[Stat], 0, 100);
		}
	}

	int32 Lives(const FString& ShipName, int32 HullStat)
	{
		const FShipDef& Def = Ship(ShipName);
		const int32 Extra = FMath::Max(0, HullStat - Def.Stats[static_cast<int32>(EEXStat::Hull)]) / 10;
		return FMath::Clamp(Def.Lives + Extra, 1, 6);
	}

	bool HasPerk(const TArray<const FEXItem*>& Modules, const TCHAR* Perk)
	{
		for (const FEXItem* Item : Modules)
		{
			const FModuleDef* Def = Item ? Find(*Item) : nullptr;
			if (Def && Def->bLegendary && Def->Perk.Equals(Perk))
			{
				return true;
			}
		}
		return false;
	}

	FFlameStyle Flame(const FEXItem* Engine)
	{
		FFlameStyle Style = Flames[FlameIndex(Engine)];
		const EEXRarity Rarity = Engine ? static_cast<EEXRarity>(Engine->Rarity) : EEXRarity::Common;
		// Rares burn longer and brighter; epics add shock diamonds and sparks; legendaries have their own flame.
		if (Rarity >= EEXRarity::Rare && Rarity < EEXRarity::Legendary)
		{
			Style.Length *= 1.15f;
			Style.Core = Style.Core * 1.15f;
		}
		if (Rarity == EEXRarity::Epic)
		{
			Style.Diamonds = FMath::Max(Style.Diamonds, 2);
			Style.bSparks = true;
		}
		return Style;
	}

	FLinearColor NitroColour(const FEXItem* Propulsion)
	{
		const FModuleDef* Def = Propulsion ? Find(*Propulsion) : nullptr;
		return NitroColours[Def ? FMath::Clamp(Def->Look, 0, static_cast<int32>(UE_ARRAY_COUNT(NitroColours)) - 1) : 0];
	}

	FLinearColor ReactorGlow(const FEXItem* Reactor)
	{
		const FModuleDef* Def = Reactor ? Find(*Reactor) : nullptr;
		return ReactorColours[Def ? FMath::Clamp(Def->Look, 0, static_cast<int32>(UE_ARRAY_COUNT(ReactorColours)) - 1) : 0];
	}

	void OpenCache(EEXCache Kind, FRandomStream& Random, int32& NextSerial, TArray<FEXItem>& OutItems, TArray<EEXConsumable>& OutConsumables)
	{
		const FCacheDef& Def = Cache(Kind);
		const int32 Components = Kind == EEXCache::Elite ? Random.RandRange(5, 6) : Random.RandRange(4, 6);
		TArray<EEXFamily> Families;
		for (int32 F = 0; F < FamilyCount; ++F)
		{
			Families.Add(static_cast<EEXFamily>(F));
		}
		for (int32 Index = Families.Num() - 1; Index > 0; --Index)
		{
			Families.Swap(Index, Random.RandRange(0, Index));
		}
		TArray<float> Odds;
		Odds.Append(Def.Odds, 4);
		TArray<EEXRarity> Rarities;
		for (int32 K = 0; K < Components; ++K)
		{
			Rarities.Add(static_cast<EEXRarity>(Weighted(Random, Odds)));
		}
		if (Kind == EEXCache::Advanced && !Rarities.ContainsByPredicate([](EEXRarity R) { return R >= EEXRarity::Rare; }))
		{
			Rarities[0] = EEXRarity::Rare;
		}
		if (Kind == EEXCache::Elite)
		{
			Rarities.Sort();
			if (!Rarities.Contains(EEXRarity::Epic))
			{
				Rarities.Last() = EEXRarity::Epic;
			}
			for (int32 K = 0; K < Rarities.Num(); ++K)
			{
				int32 RareOrBetter = 0;
				for (const EEXRarity R : Rarities)
				{
					RareOrBetter += R >= EEXRarity::Rare ? 1 : 0;
				}
				if (RareOrBetter >= 4)
				{
					break;
				}
				if (Rarities[K] < EEXRarity::Rare)
				{
					Rarities[K] = EEXRarity::Rare;
				}
			}
		}
		const int32 First = OutItems.Num();
		for (int32 K = 0; K < Components; ++K)
		{
			const TArray<const FModuleDef*> Defs = Regular(Families[K % Families.Num()]);
			if (Defs.Num() > 0)
			{
				OutItems.Add(Roll(*Defs[Random.RandRange(0, Defs.Num() - 1)], Rarities[K], Random, NextSerial++));
			}
		}
		if (Kind == EEXCache::Elite && Random.FRand() < 0.04f && OutItems.Num() > First)
		{
			// One piece goes up to legendary, preferably of a family a legendary has (keeps the variety).
			TArray<const FModuleDef*> Legends;
			for (const FModuleDef& M : Catalogue())
			{
				if (M.bLegendary)
				{
					Legends.Add(&M);
				}
			}
			const FModuleDef* Legend = Legends[Random.RandRange(0, Legends.Num() - 1)];
			int32 Slot = INDEX_NONE;
			for (int32 K = First; K < OutItems.Num(); ++K)
			{
				const FModuleDef* M = Find(OutItems[K]);
				if (M && M->Family == Legend->Family)
				{
					Slot = K;
					break;
				}
			}
			if (Slot == INDEX_NONE)
			{
				Slot = First;
				for (int32 K = First + 1; K < OutItems.Num(); ++K)
				{
					Slot = OutItems[K].Value > OutItems[Slot].Value ? K : Slot;
				}
			}
			OutItems[Slot] = Roll(*Legend, EEXRarity::Legendary, Random, OutItems[Slot].Serial);
		}
		for (int32 K = Components; K < 10; ++K)
		{
			OutConsumables.Add(static_cast<EEXConsumable>(Random.RandRange(1, ConsumableCount - 1)));
		}
	}

	void RollShop(FRandomStream& Random, int32& NextSerial, TArray<FEXItem>& Out)
	{
		Out.Reset();
		TArray<const FModuleDef*> Defs;
		for (const FModuleDef& Def : Catalogue())
		{
			if (!Def.bLegendary)
			{
				Defs.Add(&Def);
			}
		}
		const EEXRarity Rotation[] = { EEXRarity::Common, EEXRarity::Common, EEXRarity::Common, EEXRarity::Uncommon, EEXRarity::Uncommon, EEXRarity::Rare };
		for (const EEXRarity Rarity : Rotation)
		{
			Out.Add(Roll(*Defs[Random.RandRange(0, Defs.Num() - 1)], Rarity, Random, NextSerial++));
		}
	}

	void RollBotBuild(const FString& ShipName, int32 Skill, FRandomStream& Random, int32& NextSerial, TArray<FEXItem>& Out)
	{
		Out.Reset();
		Out.SetNum(FamilyCount);
		Skill = FMath::Clamp(Skill, 0, 2);
		static const float Odds[3][4] = { { 0.75f, 0.22f, 0.03f, 0.0f }, { 0.45f, 0.38f, 0.15f, 0.02f }, { 0.20f, 0.40f, 0.32f, 0.08f } };
		TArray<float> Weights;
		Weights.Append(Odds[Skill], 4);
		for (int32 F = 0; F < FamilyCount; ++F)
		{
			if (Random.FRand() >= 0.35f + 0.15f * Skill)
			{
				continue;
			}
			TArray<const FModuleDef*> Fit;
			for (const FModuleDef& Def : Catalogue())
			{
				if (!Def.bLegendary && Fits(Def, ShipName, static_cast<EEXFamily>(F)))
				{
					Fit.Add(&Def);
				}
			}
			if (Fit.Num() > 0)
			{
				Out[F] = Roll(*Fit[Random.RandRange(0, Fit.Num() - 1)], static_cast<EEXRarity>(Weighted(Random, Weights)), Random, NextSerial++);
			}
		}
		if (Skill >= 2 && Random.FRand() < 0.03f)
		{
			TArray<const FModuleDef*> Legends;
			for (const FModuleDef& Def : Catalogue())
			{
				if (Def.bLegendary && Fits(Def, ShipName, Def.Family))
				{
					Legends.Add(&Def);
				}
			}
			if (Legends.Num() > 0)
			{
				const FModuleDef* Legend = Legends[Random.RandRange(0, Legends.Num() - 1)];
				Out[static_cast<int32>(Legend->Family)] = Roll(*Legend, EEXRarity::Legendary, Random, NextSerial++);
			}
		}
	}

	int32 PlaceReward(int32 Place)
	{
		// Doc 03 sec. 3, times 0.70 for a 10-15 minute expedition.
		static const int32 Table[] = { 1600, 1300, 1100, 950, 850, 750, 675, 600, 550, 500, 450, 425, 400, 375, 350, 325, 300, 275, 250, 225 };
		const int32 Index = FMath::Clamp(Place - 1, 0, static_cast<int32>(UE_ARRAY_COUNT(Table)) - 1);
		return Round10(Table[Index] * 0.70f);
	}

	TArray<int32> SelectLosses(const TArray<FEXItem>& Carried, int32 InsuredSerial, FRandomStream& Random)
	{
		TArray<int32> Pool;
		for (int32 Index = 0; Index < Carried.Num(); ++Index)
		{
			if (Carried[Index].IsValid() && Carried[Index].Serial != InsuredSerial)
			{
				Pool.Add(Index);
			}
		}
		TArray<int32> Lost;
		TArray<float> Weights;
		while (Lost.Num() < MaxLost && Pool.Num() > 0)
		{
			Weights.Reset();
			for (const int32 Index : Pool)
			{
				Weights.Add(static_cast<float>(FMath::Max(1, Carried[Index].Value)));
			}
			const int32 Pick = Weighted(Random, Weights);
			Lost.Add(Pool[Pick]);
			Pool.RemoveAt(Pick);
		}
		return Lost;
	}
}
