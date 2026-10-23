from __future__ import annotations

import random
from dataclasses import dataclass, field
from io import StringIO
from typing import Any

from morkbotted.security import MAX_EQUIPMENT_ITEMS, escape_discord_text, validate_text


STAT_NAMES = ("agility", "presence", "strength", "toughness")
FAREWELL_EDITABLE_FIELDS = (
    "name", "agility", "presence", "strength", "toughness", "hp", "max_hp",
    "omens", "silver", "ammo", "shock", "powers", "firearm", "sidearm",
    "armor", "reason", "battle_scar", "vice", "specialty", "history", "notes",
)

FAREWELL_NUMERIC_RANGES = {
    "agility": (-3, 6),
    "presence": (-3, 6),
    "strength": (-3, 6),
    "toughness": (-3, 6),
    "hp": (-100, 1000),
    "max_hp": (1, 1000),
    "omens": (0, 1000),
    "silver": (0, 1_000_000),
    "ammo": (0, 1000),
    "shock": (0, 1000),
    "powers": (0, 1000),
}

FAREWELL_TEXT_VALIDATORS = {
    "name": "name",
    "firearm": "equipment",
    "sidearm": "equipment",
    "armor": "equipment",
    "reason": "background",
    "battle_scar": "background",
    "vice": "background",
    "specialty": "description",
    "history": "background",
    "notes": "note",
}

REASONS_FOR_ENLISTMENT = [
    "You had no choice: enlist or be hung for your crimes.",
    "As a prisoner, you developed an obsession with brutality and pain.",
    "You wage war for the greater good of your god.",
    "Killing is your business, and business is good.",
    "You were exiled from your village and had nowhere else to go.",
    "You desire wanton, bloody, terrifying hedonism.",
    "An incurable disease ails you; you are not long for this world anyway.",
    "You are addicted to the roar of flames and blasts of shrapnel.",
    "You were seduced by the morose.",
    "Being the oldest, your mother signed the papers for you.",
    "You struggle with a ghastly addiction to the taste of blood.",
    "You seek the honor of burial among the flowers in Newfield.",
    "Your farmstead was destroyed and your family killed.",
    "A misguided sense of justice steers you.",
    "Starvation is a great motivator. They feed grvnts... mostly.",
    "The land changed, wiping out your way of life. You have nothing to return to.",
    "Star-crossed lovers fight on two sides. You want to be a bayonet's length away.",
    "You do not remember why you enlisted.",
    "Glory calls for you. Your corpse will be stepped on.",
    "Rising from the dead, you resume your past life.",
]

BATTLE_SCARS = [
    "Crooked facial scar stuffed with horsehair",
    "Infected finger on one hand",
    "Burnt eye with flaking skin and a pungent smell",
    "Constant concussion and headaches",
    "Nose replaced by a gash",
    "Razor wire embedded in an arm (d6)",
    "Shortened stride from a Shinripper",
    "Permanent thousand-league stare",
    "Painfully migrating shrapnel",
    "d6 missing teeth",
    "Broken blood vessel in one eye",
    "d2 fractured ribs that rattle while running",
    "Weak knees and hunched posture",
    "Massive, distracting hematoma",
    "SLAGGVARA shrapnel protruding like a demon horn; fatal if removed",
    "Melted gas-mask face that still works",
    "Crudely severed hand",
    "Ripped corner of the mouth exposing teeth",
    "Stab wound that never heals, stuffed with gauze",
    "Battle tinnitus that blocks out everything when in SHOCK",
    "Disfiguration from Dark Thoughts",
    "Terminal cough that hacks up small puffs of GAS",
    "Ripped throat from an attempted assassination",
    "Bite mark from something inhuman",
    "Flayed scalp dangling in the wind",
    "Snaggletooth punctured through the lip",
    "Arrow lodged in the femoral artery",
    "Broken foot crushed by steel treads",
    "SLAGGVARA tattoo that will not stop itching",
    "Shoulder that pops out of place at will",
    "Deep rope burns on the palms",
    "Hole in the skull; helmets never fit",
    "Severe contusion that looks oddly like a face",
    "Soggy, necrotic toes",
    "Lacerated arm that probably needs treatment",
    "Slow-leaking abscess that smells of offal",
]

VICES = [
    "Fondling a Shinripper",
    "Confessing war crimes to a Cynically Cursed Chaplain",
    "Burning through an entire pack of smokes in a night",
    "Writing horrible poetry and forcing others to listen",
    "Holding a hand above flames until the pain is too great",
    "Winning bets made with fellow grvnts",
    "Endlessly counting ammunition",
    "Reading every collected dog tag; you must have more",
    "Walking among corpses looking for a familiar face",
    "Biting fingernails far too short",
    "Juggling grenades; the more, the better",
    "Meticulously and eerily cleaning weapons",
    "Overindulging in drink until passing out",
    "Donning a gas mask for no reason",
    "Snorting crushed SLAGG",
    "Dry shaving with a jagged, rusty bayonet",
    "Creating morose paintings of the day's atrocities",
    "Building useless wooden crosses",
    "Writing letters to no one",
    "Cataloging every injury in a diary",
]

NICKNAMES = (
    "Roach Broken Dogtag Rat Mother Lucky Jerky Target Lover Noisy Killer Tiny Ballerina Scar Runner "
    "Speedball High-and-Tight Gunner Che Sisu Tooth Grit Nothing Writer Sib Jackass Slim Lazy Havi Narrow "
    "Tallow Gear Steamer Nothing Gore Rat Leak Tack Slaggy Maker Boom-Boom Soup Bones Old-Dog Pest Squeak "
    "Nightlife Tower Toothless Cy Snow Monster Face Foreigner Thumper Drip Sarkash Meat Sticky Pusher Gritty "
    "Solo Hybrid Brain Buster Cruise Thief Gorgon Yo Stab Bark Chunk Nobody Retch Doom Pinky Flash Mark Frost "
    "Milky Boing-Boing Knot Crusher Moth Player Bear Johnny Flush Cleaner Gross Nope Drag Drug Pop Eraser "
    "Moonchild Smiles Dragline Ender Borg"
).split()

FIREARMS = [
    "Cvlt .45 (d4 pistol; no melee or Ammo penalty)",
    "666 Shooter (d4 revolver, SCOPED)",
    "Vermin Maimer (d6 sawed-off shotgun; HEAVY in melee)",
    "Dual Cvlt .45s (2d4, no Ammo penalty, two-handed)",
    "Schleswig Sprayer (d6, d2 targets per Ammo, two-handed)",
    "Malevolent Rifle (d8, two-handed, IMPACT 1)",
    "Malevolent Rifle with Bayonet (d8 ranged/d4 melee, two-handed, IMPACT 1)",
    "Precise Rifle (d10, two-handed, SCOPED)",
    "Boom Lance (d10, two-handed, BLAST 2, HEAVY)",
    "Slug Launcher (d12, Strength DR12, two-handed, IMPACT 2, SHOCK)",
]

SIDEARMS = [
    "d3 Smog Poppers (Full cover smoke)",
    "d3 SLAGG Bangs (-2 to rolls for d2 turns, SHOCK)",
    "d3 Scream Grenades (d4, BLAST 3, HEAVY)",
    "Punch Dagger (d4, SHOCK)",
    "Fire Spear (d6 melee/d8 ranged, BURN 1 once per combat)",
    "Shorter Sword (d6; may be fixed as a bayonet)",
    "Barbed Wire Club (d6; ignores helmets)",
    "Short Bow (d6; 10 + Presence arrows)",
    "Zweihander (d10, HEAVY)",
    "d2 Shinrippers (3d4, IMPACT 1, HEAVY, SHOCK; unstable)",
]

ARMOR = [
    "Tier 0: no armor (peasant rags)",
    "Tier 1: -d2 damage (rat-chewed gambison or thatched vest)",
    "Tier 2: -d4 damage (scrap metal or splint mail)",
    "Tier 2: -d4 damage plus helmet",
    "Tier 3: -d6 damage (crawler bodywork or howler-bear pelts)",
    "Tier 3: -d6 damage plus helmet",
    "Tier 4: -d8 damage (Lobster Armor; deep water is deadly)",
]

CARRY_GEAR = [
    "Nothing; supplies were low",
    "Nothing; supplies were low",
    "Bandolier (carries unspent Ammo)",
    "Side Satchel (+2 normal-sized items)",
    "Ratty ol' Haversack (+6 normal-sized items)",
    "Pack Mule (too starved to ride)",
]

COMBAT_GEAR = [
    "Entrenching Tool (d4)", "SLAGG Dip (d4 applications; adds a weapon keyword)",
    "Small Shield", "Ammo Box (+d4 Ammo)", "Field Dress Kit (Presence+4 uses; heals d6)",
    "Ammo Belt", "Scope", "Large Shield", "Gas Mask",
    "Tergol's Secret Cocktail (d4, SHOCK, BURN 3)", "Helmet", "Random War Scroll",
]

PERSONAL_GEAR = [
    "Pack of smokes", "Wire cutters", "Compass", "Last letter from home", "Prayer beads",
    "Grappling hook", "Pocketful of bent nails", "d2 signal flares", "Repair kit",
    "Dead friend's dog tags", "20 ft barbed-wire coil", "Raw piece of SLAGG",
]

HOMESICK_KEEPSAKES = [
    "d4 Letters from Home (d4 damage plus a random weapon keyword)",
    "Stop Watch (1-in-4 chance to block non-BLAST damage)",
    "Purple Heart Poetry (spend 1 Power to add current SHOCK to a target)",
    "Lovesick painting (cast one random War Scroll per day automatically)",
]

WAR_SCROLLS = [
    "Nay-Palm", "Bite the Bullet", "For Whom the Bell Tolls", "Afraid to Shoot Strangers",
    "Lay of the Land", "Red Badge of Courage", "GAS!", "Trenchfoot", "Full Metal Jacket",
    "Apocalypse Later", "Night and Day", "Black Candles Burn, All Minds Align Evenly",
    "Misfire", "Tumbling Down", "Gunpowder Plot", "Magnum Opus", "VEX's Assistant",
    "Take Me to Your Leader", "The Trooper", "War Pigs",
]

WAR_SCROLL_DETAILS = {
    "Nay-Palm": "Choose d3 creatures. They ignite and die in d4 turns; their flames spread to anything they touch.",
    "Bite the Bullet": "A target already wounded by a firearm immediately suffers that firearm's damage again. This effect has IMPACT 4.",
    "For Whom the Bell Tolls": "Everyone within roughly 30 feet suffers SHOCK.",
    "Afraid to Shoot Strangers": "Every firearm near the reader jams for d4 turns.",
    "Lay of the Land": "Spectral movement reshapes the battlefield and raises Full cover from the earth.",
    "Red Badge of Courage": "One creature ignores SHOCK and spends no Ammo for d4 rounds, but enemies prioritize that creature.",
    "GAS!": "The immediate area fills with toxic GAS.",
    "Trenchfoot": "The ground traps one target. Its armor loses one Tier each turn until it passes Strength DR12 to escape.",
    "Full Metal Jacket": "Sacrifice d2 Ammo and gain one Tier of armor for each point sacrificed.",
    "Apocalypse Later": "Reduce d2 allies' SHOCK to zero. Each suffers d10 SHOCK the following morning.",
    "Night and Day": "Change day into night or night into day, then trigger equipment that refreshes on the next day.",
    "Black Candles Burn, All Minds Align": "Redistribute the squad's combined SHOCK as evenly as possible among nearby allied grvnts.",
    "Misfire": "All Ammo within roughly 30 feet explodes for d4 damage.",
    "Tumbling Down": "Nearby structures collapse to the reader's level. Occupants suffer d3 damage per demolished level.",
    "Gunpowder Plot": "Use a Warlord Order twice during the mission. The Warlord dies when the mission ends.",
    "Magnum Opus": "Summon a phantom 666 Shooter that attacks d6 targets; on most results, the reader is also targeted.",
    "VEX's Assistant": "Blue light removes d2 random allies who fail Presence and d4 enemies from the battlefield to an unknown destination.",
    "Take Me to Your Leader": "Gain a random Warlord Order belonging to an opposing faction.",
    "The Trooper": "d2 allies may close on a firearm-wielding enemy while that enemy fires.",
    "War Pigs": "A ravenous stampede deals 4d10 damage divided among everything in its path.",
}

SHOCK_EFFECTS = [
    "The Shakes — always act last in Initiative.",
    "Primal Fear — the next SHOCK increase uses d6.",
    "Thousand-League Stare — leave an item behind.",
    "Visions of Death — subtract 1 from all damage rolls.",
    "Jammed — unable to choose a target for d2 rounds.",
    "Blind Fire — immediately fire at the nearest enemy against DR16.",
    "Despair — lose an Omen; if none remain, suffer Dark Thoughts.",
    "Dark Thoughts — harm yourself with your Side Arm.",
    "Panic — flee toward safety and inflict SHOCK on nearby allies.",
    "Confusion — attack the nearest comrade with your strongest weapon.",
    "Abject Sorrow — drop your weapons and run directly at the enemy.",
    "Endgame — die where you stand.",
]

FAREWELL_RULE_REFERENCE = {
    "combat": (
        "Roll d6 for group Initiative: enemies act first on 1–3 and players on 4–6. Melee tests Strength DR12, ranged attacks test "
        "Presence DR12, and defense tests Agility DR12, all adjusted by cover or Aim. A natural 20 improves the result; a natural 1 causes a fumble."
    ),
    "stats": (
        "Stats are modifiers, normally from -3 to +3 at enlistment. Roll d20 plus the relevant Stat and meet or beat the DR. "
        "Toughness resists SHOCK, GAS, cold, and heat; Agility handles defense, stealth, and explosions; Presence covers shooting, "
        "perception, and War Scrolls; Strength covers melee, throwing, grappling, and carrying heavy squad equipment."
    ),
    "hp": (
        "A grvnt at 0 or -1 HP rolls on the Downed table and may recover, suffer SHOCK, or die. At -2 HP or lower, death is certain. "
        "Starting HP can never be below 1."
    ),
    "omens": (
        "Omens refresh to the class allotment at dawn after all have been spent. Spend one to maximize attack damage, reroll any die, "
        "reduce incoming damage by d6, cancel a critical or fumble, or lower one test's DR by 4."
    ),
    "ammo": (
        "Ammo is an abstract supply rather than individual rounds. Roll the class's Ammo die at dawn only when completely empty. "
        "Some weapons spend Ammo differently or ignore it entirely."
    ),
    "powers": (
        "At each grey dawn, Powers equal Presence + d4, with a minimum of zero in this bot. Spend Powers on class specialties or War Scroll effects. "
        "Reading a War Scroll normally tests Presence DR12; failure costs d2 HP and d2 SHOCK, while a fumble destroys the scroll and causes an accident."
    ),
    "shock": (
        "When SHOCK is inflicted, test Toughness DR14. On failure, add d4 SHOCK and immediately resolve the effect matching the new total. "
        "Reducing SHOCK does not retrigger effects. Rest, food, drink, and some abilities can provide relief."
    ),
    "firearm": "Ranged firearm attacks normally test Presence DR12, adjusted by Aim and cover. Firearms cannot be reloaded in melee and are +2 DR to fire there.",
    "sidearm": "Side Arms support close combat, emergency ranged attacks, grenades, shields, and specialized battlefield effects. Their listed keywords apply in order.",
    "armor": "Armor reduces incoming damage by its die. HEAVY hits can destroy a Tier. Helmets may be broken to prevent all damage from one attack.",
    "gear": "SHIT is the grvnt's carried support equipment. Capacity comes from the rolled carrier plus two normal-sized items unless another rule changes it.",
    "reason": "Reason for Enlistment is a roleplaying prompt explaining why this grvnt entered the war; it has no default mechanical effect.",
    "battle_scar": "A Battle Scar records lasting wartime injury. Unless its entry gives a rule, treat it as descriptive until the GM makes it relevant.",
    "vice": "A Vice is how the grvnt copes with the war. Vices can help contextualize rest, addiction, withdrawal, and roleplay.",
    "weapon_keywords": (
        "SCOPED grants automatic Aim but cannot be used in melee. BLAST (X) damages X nearby targets. IMPACT (X) ignores X Armor Tiers. "
        "HEAVY degrades cover and destroys one Armor Tier on a hit. SHOCK forces Toughness DR14 or a d4 SHOCK result. "
        "BURN (X) deals d4 damage for the next X rounds. Apply keywords in that order."
    ),
    "cover": (
        "Partial cover adjusts attacks and defense by 2 DR; Full cover adjusts them by 4 DR; Total cover prevents targeting except from HEAVY attacks. "
        "HEAVY degrades Total to Full, Full to Partial, and destroys Partial cover."
    ),
    "rest": (
        "A smoke and a ration restore d4 HP. A full night's sleep restores d6 HP and relieves d2 SHOCK. Without rations, resting cannot heal; "
        "after two days of starvation, lose d4 HP daily. Infection prevents healing and instead costs d6 HP per day."
    ),
}

CLASS_EXTRA_REFERENCE = {
    "expendable-sapper": (
        "Throwing grenades is 2 DR easier, and the Sapper is immune to BLAST damage. Whenever Ammo is rerolled, also roll d3 on Side Arms to restock grenades."
    ),
    "homesick-rifleman": (
        "In addition to a special Malevolent Rifle, roll one keepsake: trapped Letters from Home, a damage-blocking Stop Watch, "
        "SHOCK-channeling Purple Heart Poetry, or a Lovesick painting that enables one automatic random War Scroll each day."
    ),
    "altered-mercenary": (
        "Add the rolled beast number (1–6) to starting HP. Altered Mercenaries cannot use firearms or armor of Tier 2 or higher."
    ),
    "embedded-one": (
        "Once per day, summon the chosen Ether. Movement grants the squad d6 immediate actions. Growth enlarges or shrinks nearby creatures. "
        "Decay destroys firearms, armor, or flesh based on 3d6. Interdependence supplies four dice allies may add or subtract and clears squad SHOCK. "
        "Curiosity rolls five dice to acquire three pieces of SHIT. Time rolls six dice: low totals inflict enemy SHOCK, middle totals force Morale, and high totals deal damage."
    ),
    "radiant-bannerman": (
        "The fused Bannerspear deals d6 with IMPACT 1 and is visible from far away. Banner color determines the specialty."
    ),
    "new-world-engineer": (
        "Begin with two Muskoxen (HP 14) hauling prepared structures. Choose two different structures and construct each once per mission."
    ),
    "despondent-interpreter": (
        "Unthreatening gives a 1-in-2 chance to be ignored in combat. When nearby enemies test Morale, improve the result by 1. "
        "Record twenty listed battlefield events; every three completed events grants a permanent squad bonus, chosen once from the class list."
    ),
    "sadistic-soldier": (
        "All melee weapons deal +d2 damage. Each melee kill yields a random trophy with a paired benefit and penalty: ears trade Toughness for Agility, "
        "eyes trade Strength for Presence, teeth trade max HP for Armor, noses trade Agility for Toughness, fingers trade Armor for damage, and tongues trade Presence for max HP. "
        "Discard trophies only while resting. This class can never be Promoted."
    ),
}


@dataclass(frozen=True)
class FarewellClass:
    slug: str
    name: str
    hp_die: int
    omens_die: int
    silver_dice: tuple[int, int, int]
    ammo: tuple[int, int, int] | None
    stat_adjustments: dict[str, int]
    firearm_die: int | None
    armor_die: int | None
    sidearm_die: int | None = 10
    war_scrolls: int | tuple[int, int] = 0
    fixed_firearm: str = ""
    fixed_gear: tuple[str, ...] = ()
    specialties: tuple[str, ...] = ()
    histories: tuple[str, ...] = ()
    notes: str = ""


CLASSES = [
    FarewellClass("grizzled-veteran", "Grizzled Veteran", 10, 2, (2, 6, 10), (1, 3, 0),
                  {"toughness": 2, "agility": -2}, 10, 6,
                  specialties=(
                      "Battle Buddy Bayonet — d6; -2 DR on all SHOCK tests",
                      "Troll-Blooded — spend a turn to heal d6 HP",
                      "Bear-zerker Rage — attack twice each turn, once ranged and once in melee",
                      "Skulls Unit — d4+1 tethered skeletons use your Presence and deal d4 each",
                      "The Tank Slicer — Zweihander d10, IMPACT 2",
                      "Thunderhorse — HP 12, DR10; hooves d6 or spend 1 Power for fiery breath d8, BURN 2",
                  ),
                  histories=("Sole survivor of SLAGG sabotage", "Charged across No Man's Land", "Betrayed and left for dead", "Court-martialed for insubordination", "Survived GAS and shellfire", "Prematurely buried by your company")),
    FarewellClass("expendable-sapper", "Expendable Sapper", 6, 2, (1, 6, 10), (1, 3, 0),
                  {"agility": 2, "strength": -2}, 10, 4, 3,
                  specialties=(
                      "Thumper — all your items gain HEAVY",
                      "Foresight — spend 1 Power to detonate a hidden Shinripper; 1-in-6 it is the wrong one",
                      "POAB — once per mission, everything within 50 ft takes d12+2, IMPACT 3, HEAVY, SHOCK",
                      "Juggernaut — Lobster Armor and a d4 HEAVY punch; feed it SLAGG for d8",
                      "Death From Below — tunnel for a turn; weapons inside gain IMPACT 2",
                      "Sneaky Fvck — stealth is -2 DR; unlock standard locks or commandeer empty vehicles with Agility",
                  ),
                  histories=("A hidden Shinripper under a parent's pillow", "Your first grenade mishap", "Point-blank cannon fire", "A Smog Popper in your barracks", "A lucky Boom Lance strike", "Your first mushroom cloud")),
    FarewellClass("recluse-marksman", "Recluse Marksman", 6, 4, (1, 6, 10), (1, 4, 0),
                  {"presence": 2, "strength": -2}, None, 2,
                  fixed_firearm="More-Precise Rifle (d10, SCOPED, IMPACT 1)",
                  specialties=(
                      "Night Stalker — -2 DR on Presence at night; rest while On Watch",
                      "Coriolis Effect — 1-in-6 a shot hits a second grvnt for d6; twice as likely from elevation",
                      "Pet Raven — spend 1 Power to see through it for miles; +2 DR when interacting with people",
                      "All Quiet — spend 1 Power for an unerring silent shot that inflicts SLEEP for d4 turns",
                      "Calm the Nerves — crit on 18–20 while smoking or indulging a vice; lower SHOCK by 1",
                      "Occult Obscurity — spend 1 Power to remain unlocatable until after your next d4 attacks",
                  ),
                  histories=("Shot the lit smoke from an enemy's mouth", "Shot through a rival marksman's scope", "Assassinated a key officer", "Killed a flying Altered in darkness", "Ignited a SLAGG deposit", "An unconfirmed impossible shot")),
    FarewellClass("homesick-rifleman", "Homesick Rifleman", 6, 2, (3, 6, 10), (1, 4, 0), {}, None, 4,
                  fixed_firearm="Malevolent Rifle (d8, two-handed, IMPACT 1)",
                  specialties=(
                      "Legion, the Haunted Rifle — spend 1 Power for its ghost to deal d8 without Ammo",
                      "The Galgen Beheader — oversized d8 bayonet; melee crits on 18–20",
                      "R.O.D. Grenades — spend 1 Power to add any grenade type to the next rifle attack",
                      "Basilisk Carbine — no melee penalty; gains BLAST 2 and SHOCK in melee",
                  ),
                  histories=("Your family plans to eat you", "Write home; they need hearth fuel", "Clear the family curse", "They never noticed you left", "Block bullets for better grvnts", "Always wear a helmet")),
    FarewellClass("cynically-cursed-chaplain", "Cynically Cursed Chaplain", 6, 4, (2, 6, 20), (1, 2, 0),
                  {"toughness": -2, "presence": 1, "strength": 1}, None, 4, war_scrolls=(1, 2),
                  specialties=(
                      "Cross of the Carpenter Saint — d8; lower SHOCK by 1 to defend as a Large Shield",
                      "Fire and Brimstone — Presence DR12 inflicts a random SHOCK no greater than yours",
                      "Galgorian Chanting — Presence DR12 minus SHOCK lets all grvnts reroll daily resources",
                      "Grief Seed — spend 1 Power and all SHOCK to deal that much damage, BLAST 3",
                      "The Sorrow of Salvation — each dawn gain a temporary random firearm capped by your SHOCK",
                      "Thurible of Indignation — d6, BURN 1; suffering SHOCK triggers an attack on the nearest target",
                  ),
                  notes="May suffer d2 SHOCK in place of any SHOCK test."),
    FarewellClass("arcane-medic", "Arcane Medic", 6, 2, (2, 6, 20), (1, 2, 0),
                  {"toughness": 2, "strength": -2}, 6, 6, war_scrolls=1,
                  fixed_gear=("Field Dress Kit",),
                  specialties=(
                      "The Artist at Work — carve a patient for +d2 daily healing but +1 on their SHOCK table",
                      "Voynichian Script of Last Rites — revive a recently felled creature at half HP, once per creature",
                      "Leech Therapy — -d2 damage, then cures illness and lowers SHOCK after d2 days",
                      "Unguent — spend 1 Power to craft d4 uses with stacking restorative effects",
                      "Abscission Obsession — spend 1 Power to prevent Broken; every two harvested organs earns Promotion",
                      "Avenging Aegis — planted shield provides indestructible Full cover",
                  )),
    FarewellClass("altered-mercenary", "Altered Mercenary", 8, 2, (2, 6, 10), None,
                  {"toughness": 1, "strength": 1, "presence": -2}, None, 2,
                  specialties=(
                      "Schunk-Striped — taking damage or SHOCK sprays putrid GAS at its source",
                      "Arach-Webbed — spend 1 Power to immobilize with razor web; d6 damage per turn",
                      "Falchon-Winged — fly with -2 DR Agility tests; talons deal d10",
                      "Hyena-Throated — bite d6 heals d2; spend 1 Power and Presence DR8 to cast a random War Scroll",
                      "Krok-Toothed — Agility DR10 to gain Partial cover and attack unseen at DR8 for d8, SHOCK",
                      "Kongoose-Tusked — 2d6 split across two adjacent targets, IMPACT 1; permanent -d6 armor",
                  ),
                  notes="Cannot use firearms or Tier 2+ armor."),
    FarewellClass("embedded-one", "Embedded One", 8, 4, (0, 0, 0), None,
                  {"toughness": -2, "agility": 1, "presence": 1}, None, None, None,
                  specialties=(
                      "Movement Ether — Super Speed gift; Parallax covering (DR16 to hit)",
                      "Growth Ether — Blacktrunk Club d8, SHOCK; Creeping Vines -d2 and Partial cover",
                      "Decay Ether — Undead Fox d6, IMPACT 1; Animal Hides -d4 and Partial cover",
                      "Interdependence Ether — fists d4 or Presence DR12 to force Morale; enemies roll +2 Morale",
                      "Curiosity Ether — roll d10 firearm and d6 armor each morning",
                      "Time Ether — rewind an ally's attack; when hit, immediately take another turn",
                  ),
                  notes="Ontological Oddity: test Toughness to become invisible; cannot attack or heal while invisible."),
    FarewellClass("radiant-bannerman", "Radiant Bannerman", 6, 3, (2, 6, 10), (1, 3, 0),
                  {"toughness": -2, "presence": 2}, 4, 2, None,
                  fixed_gear=("Bannerspear (d6, IMPACT 1)",),
                  specialties=(
                      "Vampiric Garnet — natural armor from d4+1 on the armor table; blocked damage forces Morale",
                      "Somber Ash — spend 1 Power to SILENCE d4 creatures for d4 turns",
                      "Deepest Cobalt — Bannerspear kills grant you and nearby allies d4 armor next defense",
                      "Deathly Coal — spend 1 Power: d6 enemies suffer Dark Thoughts and allies take d4 SHOCK",
                      "Shining Snow — spend 1 Power: allies gain d2 Omens/Powers, heal d4, or lower SHOCK d3",
                      "Powerful Emerald — spend 1 Power to adjust an allied Initiative or SHOCK test by d4",
                  )),
    FarewellClass("new-world-engineer", "New World Engineer", 8, 4, (1, 6, 10), (1, 4, 2),
                  {"agility": 2, "presence": -2}, 6, 4,
                  fixed_gear=("Two Muskoxen (HP 14)",),
                  specialties=(
                      "Hunker Dory — Total-cover reinforced box for two grvnts",
                      "So Hwatcha Want — mobile 2d6-rocket battery; d2 each, IMPACT 2; costs 1 SLAGG",
                      "Tower of Power — d3-level tower; +1 Presence per level and Partial cover",
                      "No Tanks — tank traps stop armored enemies for d2 turns",
                      "Bridge the Gap — rapidly build a narrow squad-capacity bridge",
                      "Barbed and Ready — enemies encountering your wire take d3 damage, test Morale, or suffer SHOCK",
                  ),
                  notes="Choose two structures to construct once per mission."),
    FarewellClass("despondent-interpreter", "Despondent Interpreter", 6, 4, (1, 6, 10), (1, 2, 0),
                  {"presence": 2, "strength": -2}, 4, 4, war_scrolls=1,
                  notes="Unthreatening: 1-in-2 chance to be ignored in combat; influence nearby enemy Morale results."),
    FarewellClass("sadistic-soldier", "Sadistic Soldier", 10, 2, (1, 6, 10), (1, 2, 0),
                  {"toughness": 2, "presence": -2}, 10, 2, None,
                  fixed_gear=("Punch Dagger (d4, SHOCK)",),
                  specialties=(
                      "Brains — eating them grants one memory from the former owner",
                      "Bones — hollowed instruments drive prolonged listeners mad",
                      "Guts — craft harvested offal into hideous items",
                      "Excrement — attackers risk infection from your powerful filth",
                  ),
                  notes="All melee weapons deal +d2 damage. You can never be Promoted."),
]

CLASS_BY_SLUG = {item.slug: item for item in CLASSES}


@dataclass
class FarewellCharacter:
    user_id: int
    discord_name: str
    name: str
    class_slug: str
    class_name: str
    agility: int
    presence: int
    strength: int
    toughness: int
    hp: int
    max_hp: int
    omens: int
    silver: int
    ammo: int
    shock: int
    powers: int
    reason: str
    battle_scar: str
    vice: str
    firearm: str = "None"
    sidearm: str = "None"
    armor: str = "None"
    specialty: str = ""
    history: str = ""
    gear: list[str] = field(default_factory=list)
    war_scrolls: list[str] = field(default_factory=list)
    notes: str = ""
    id: int | None = None

    def to_payload(self) -> dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "FarewellCharacter":
        return cls(**payload)

    def sheet_lines(self) -> list[str]:
        esc = escape_discord_text
        lines = [
            f"**{esc(self.name)}** — {esc(self.class_name)}",
            f"HP `{self.hp}/{self.max_hp}` | Omens `{self.omens}` | Ammo `{self.ammo}` | Powers `{self.powers}` | SHOCK `{self.shock}` | Silver `{self.silver}`",
            f"Stats `AGI {self.agility:+d}` `PRE {self.presence:+d}` `STR {self.strength:+d}` `TGH {self.toughness:+d}`",
            f"Firearm: {esc(self.firearm)}",
            f"Side Arm: {esc(self.sidearm)}",
            f"Armor: {esc(self.armor)}",
            f"Reason for Enlistment: {esc(self.reason)}",
            f"Battle Scar: {esc(self.battle_scar)}",
            f"Vice: {esc(self.vice)}",
        ]
        if self.specialty:
            lines.append(f"Class Specialty: {esc(self.specialty)}")
        if self.history:
            lines.append(f"History: {esc(self.history)}")
        lines.append(
            "SHIT: "
            + (" | ".join(f"{index}. {esc(item)}" for index, item in enumerate(self.gear, start=1)) if self.gear else "None")
        )
        lines.append("War Scrolls: " + (", ".join(esc(item) for item in self.war_scrolls) if self.war_scrolls else "None"))
        if self.notes:
            lines.append(f"Rules: {esc(self.notes)}")
        return lines

    def export_text(self) -> str:
        buffer = StringIO()
        buffer.write(f"{self.name}\nFarewell to Arms REDUX grvnt\nClass: {self.class_name}\n")
        buffer.write(f"Played by: {self.discord_name}\n")
        buffer.write(f"HP: {self.hp}/{self.max_hp}  Omens: {self.omens}  Ammo: {self.ammo}  Powers: {self.powers}  SHOCK: {self.shock}  Silver: {self.silver}\n")
        buffer.write(f"AGI {self.agility:+d}  PRE {self.presence:+d}  STR {self.strength:+d}  TGH {self.toughness:+d}\n\n")
        for label, value in (("Firearm", self.firearm), ("Side Arm", self.sidearm), ("Armor", self.armor),
                             ("Reason for Enlistment", self.reason), ("Battle Scar", self.battle_scar),
                             ("Vice", self.vice), ("Class Specialty", self.specialty), ("History", self.history)):
            if value:
                buffer.write(f"{label}: {value}\n")
        buffer.write("\nSHIT\n" + "\n".join(f"- {item}" for item in self.gear or ["None"]) + "\n")
        buffer.write("\nWar Scrolls\n" + "\n".join(f"- {item}" for item in self.war_scrolls or ["None"]) + "\n")
        if self.notes:
            buffer.write(f"\nClass Rules\n{self.notes}\n")
        return buffer.getvalue().strip()


def update_farewell_field(character: FarewellCharacter, field_name: str, raw_value: str) -> str:
    normalized = field_name.casefold().strip().replace(" ", "_").replace("-", "_")
    if normalized not in FAREWELL_EDITABLE_FIELDS:
        raise ValueError("Unknown field. Use the field autocomplete list.")

    if normalized in FAREWELL_NUMERIC_RANGES:
        try:
            value = int(raw_value.strip())
        except ValueError as error:
            raise ValueError(f"{normalized.replace('_', ' ').title()} must be a whole number.") from error
        minimum, maximum = FAREWELL_NUMERIC_RANGES[normalized]
        if value < minimum or value > maximum:
            raise ValueError(
                f"{normalized.replace('_', ' ').title()} must be between {minimum} and {maximum}."
            )
        setattr(character, normalized, value)
        return f"{normalized.replace('_', ' ').title()} set to {value}."

    validator = FAREWELL_TEXT_VALIDATORS[normalized]
    value = validate_text(raw_value, validator, required=normalized == "name")
    setattr(character, normalized, value)
    return f"{normalized.replace('_', ' ').title()} updated."


def add_farewell_gear(character: FarewellCharacter, item: str) -> str:
    if len(character.gear) >= MAX_EQUIPMENT_ITEMS:
        raise ValueError(f"A grvnt can carry at most {MAX_EQUIPMENT_ITEMS} recorded items.")
    clean_item = validate_text(item, "equipment", required=True)
    character.gear.append(clean_item)
    return clean_item


def remove_farewell_gear(character: FarewellCharacter, item_number: int) -> str:
    if not character.gear:
        raise ValueError("This grvnt has no recorded SHIT to remove.")
    if item_number < 1 or item_number > len(character.gear):
        raise ValueError(f"Item number must be between 1 and {len(character.gear)}.")
    return character.gear.pop(item_number - 1)


def _roll(count: int, sides: int) -> int:
    return sum(random.randint(1, sides) for _ in range(count))


def _modifier(total: int) -> int:
    if total <= 4:
        return -3
    if total <= 6:
        return -2
    if total <= 8:
        return -1
    if total <= 12:
        return 0
    if total <= 14:
        return 1
    if total <= 16:
        return 2
    return 3


def find_farewell_class(query: str | None) -> FarewellClass | None:
    normalized = (query or "").strip().casefold()
    if not normalized:
        return None
    return next((item for item in CLASSES if normalized in {item.slug.casefold(), item.name.casefold()}), None)


def _dice_formula(dice: tuple[int, int, int] | None, *, multiplier: bool = False) -> str:
    if dice is None:
        return "None"
    count, sides, adjustment = dice
    if count == 0:
        return "None"
    base = f"{count if count != 1 else ''}d{sides}"
    if multiplier:
        return f"{base} × {adjustment}"
    return f"{base}{adjustment:+d}" if adjustment else base


def format_farewell_class_info(class_template: FarewellClass) -> str:
    adjustments = [
        f"{stat.title()} {amount:+d} to the 3d6 roll"
        for stat, amount in class_template.stat_adjustments.items()
    ]
    firearm = class_template.fixed_firearm or (
        f"roll d{class_template.firearm_die} on Firearms" if class_template.firearm_die else "no starting firearm"
    )
    sidearm = (
        f"roll d{class_template.sidearm_die} on Side Arms" if class_template.sidearm_die else "no starting Side Arm"
    )
    armor = f"roll d{class_template.armor_die} on Armor" if class_template.armor_die else "no starting armor"
    scroll_rule = class_template.war_scrolls
    if isinstance(scroll_rule, tuple):
        scrolls = _dice_formula((scroll_rule[0], scroll_rule[1], 0))
    else:
        scrolls = str(scroll_rule)

    hp_formula = f"Toughness + d{class_template.hp_die}"
    if class_template.slug == "altered-mercenary":
        hp_formula += " + beast number"
    lines = [
        f"**{class_template.name}**",
        (
            f"HP `{hp_formula}` | Omens `d{class_template.omens_die}` | "
            f"Silver `{_dice_formula(class_template.silver_dice, multiplier=True)}` | "
            f"Ammo `{_dice_formula(class_template.ammo)}`"
        ),
        "Stat rolls: " + (", ".join(adjustments) if adjustments else "plain 3d6 for every Stat"),
        f"Starting arms: {firearm}; {sidearm}; {armor}.",
    ]
    if class_template.fixed_gear:
        lines.append("Fixed gear: " + ", ".join(class_template.fixed_gear))
    if scroll_rule:
        lines.append(f"Starting War Scrolls: {scrolls}")
    if class_template.notes:
        lines.append(f"Class rules: {class_template.notes}")
    if class_template.slug in CLASS_EXTRA_REFERENCE:
        lines.append("Additional rules: " + CLASS_EXTRA_REFERENCE[class_template.slug])
    if class_template.histories:
        lines.append("Background table: " + " | ".join(class_template.histories))
    if class_template.specialties:
        lines.append("Specialties:")
        lines.extend(f"- {specialty}" for specialty in class_template.specialties)
    return "\n".join(lines)


def farewell_character_info_choices(character: FarewellCharacter) -> list[tuple[str, str]]:
    choices = [
        (f"Class: {character.class_name}", "class"),
        ("Combat basics", "combat"),
        ("Weapon keywords", "weapon_keywords"),
        ("Cover", "cover"),
        ("Rest and recovery", "rest"),
        ("Stats and tests", "stats"),
        ("HP and Downed", "hp"),
        ("Omens", "omens"),
        ("Ammo", "ammo"),
        ("Powers and War Scroll use", "powers"),
        (f"SHOCK ({character.shock})", "shock"),
        (f"Firearm: {character.firearm}", "firearm"),
        (f"Side Arm: {character.sidearm}", "sidearm"),
        (f"Armor: {character.armor}", "armor"),
        ("Reason for Enlistment", "reason"),
        ("Battle Scar", "battle_scar"),
        ("Vice", "vice"),
    ]
    if character.specialty:
        choices.insert(1, (f"Specialty: {character.specialty.split(' — ', 1)[0]}", "specialty"))
    choices.extend(
        (f"War Scroll: {scroll}", f"scroll:{index}")
        for index, scroll in enumerate(character.war_scrolls)
    )
    choices.extend(
        (f"SHIT #{index + 1}: {item}", f"gear:{index}")
        for index, item in enumerate(character.gear)
    )
    return choices


def explain_farewell_character(character: FarewellCharacter, subject: str) -> str:
    normalized = subject.casefold().strip()
    if normalized == "class":
        class_template = CLASS_BY_SLUG.get(character.class_slug)
        if class_template is None:
            raise ValueError("This grvnt's class is not in the Farewell reference catalog.")
        return format_farewell_class_info(class_template)
    if normalized == "specialty":
        if not character.specialty:
            raise ValueError("This grvnt has no recorded specialty.")
        content = f"**Class Specialty**\n{escape_discord_text(character.specialty)}"
        if character.class_slug in CLASS_EXTRA_REFERENCE:
            content += "\n\n" + CLASS_EXTRA_REFERENCE[character.class_slug]
        return content
    if normalized in {"combat", "weapon_keywords", "cover", "rest", "stats", "hp", "omens", "ammo", "powers"}:
        return f"**{normalized.replace('_', ' ').title()}**\n{FAREWELL_RULE_REFERENCE[normalized]}"
    if normalized == "shock":
        if character.shock <= 0:
            current_effect = "Current effect: none."
        else:
            effect = SHOCK_EFFECTS[min(character.shock, len(SHOCK_EFFECTS)) - 1]
            current_effect = f"Current effect at SHOCK {character.shock}: {effect}"
        return f"**SHOCK**\n{FAREWELL_RULE_REFERENCE['shock']}\n{current_effect}"
    if normalized in {"firearm", "sidearm", "armor"}:
        value = getattr(character, normalized)
        content = (
            f"**{normalized.title()}: {escape_discord_text(value)}**\n"
            f"{FAREWELL_RULE_REFERENCE[normalized]}"
        )
        if normalized in {"firearm", "sidearm"} and any(
            keyword in value.upper() for keyword in ("SCOPED", "BLAST", "IMPACT", "HEAVY", "SHOCK", "BURN")
        ):
            content += "\n\n" + FAREWELL_RULE_REFERENCE["weapon_keywords"]
        return content
    if normalized in {"reason", "battle_scar", "vice"}:
        value = getattr(character, normalized)
        return (
            f"**{normalized.replace('_', ' ').title()}**\n{escape_discord_text(value)}\n"
            f"{FAREWELL_RULE_REFERENCE[normalized]}"
        )
    if normalized.startswith("scroll:"):
        try:
            index = int(normalized.split(":", 1)[1])
            scroll = character.war_scrolls[index]
        except (ValueError, IndexError) as error:
            raise ValueError("That War Scroll is not recorded on the active grvnt.") from error
        detail = WAR_SCROLL_DETAILS.get(scroll, "No additional reference summary is available.")
        return f"**War Scroll: {escape_discord_text(scroll)}**\n{detail}\n\n{FAREWELL_RULE_REFERENCE['powers']}"
    if normalized.startswith("gear:"):
        try:
            index = int(normalized.split(":", 1)[1])
            item = character.gear[index]
        except (ValueError, IndexError) as error:
            raise ValueError("That item is not recorded on the active grvnt.") from error
        return f"**SHIT #{index + 1}: {escape_discord_text(item)}**\n{FAREWELL_RULE_REFERENCE['gear']}"
    raise ValueError("Choose a subject from autocomplete so I can find the matching reference.")


def _roll_war_scroll_count(rule: int | tuple[int, int]) -> int:
    if isinstance(rule, int):
        return rule
    return _roll(rule[0], rule[1])


def generate_farewell_character(
    *, user_id: int, discord_name: str, class_template: FarewellClass | None = None, name: str = ""
) -> FarewellCharacter:
    template = class_template or random.choice(CLASSES)
    stats = {
        stat: _modifier(_roll(3, 6) + template.stat_adjustments.get(stat, 0))
        for stat in STAT_NAMES
    }
    if template.slug == "new-world-engineer":
        specialty = " | ".join(random.sample(template.specialties, 2))
    else:
        specialty = random.choice(template.specialties) if template.specialties else ""
    beast_bonus = template.specialties.index(specialty) + 1 if template.slug == "altered-mercenary" else 0
    hp = max(1, random.randint(1, template.hp_die) + stats["toughness"] + beast_bonus)
    omens = random.randint(1, template.omens_die)
    silver = (
        _roll(template.silver_dice[0], template.silver_dice[1]) * template.silver_dice[2]
        if template.silver_dice[0]
        else 0
    )
    ammo = _roll(template.ammo[0], template.ammo[1]) + template.ammo[2] if template.ammo else 0
    shock = random.randint(1, 2)
    powers = max(0, random.randint(1, 4) + stats["presence"])

    firearm = template.fixed_firearm or (
        FIREARMS[random.randint(1, template.firearm_die) - 1] if template.firearm_die else "None"
    )
    sidearm = SIDEARMS[random.randint(1, template.sidearm_die) - 1] if template.sidearm_die else "None"
    armor = ARMOR[random.randint(1, template.armor_die) - 1] if template.armor_die else "None"

    carry_roll = random.randint(1, 6)
    gear = [CARRY_GEAR[carry_roll - 1], *template.fixed_gear]
    if template.slug == "homesick-rifleman":
        gear.append(random.choice(HOMESICK_KEEPSAKES))
    extra_scrolls = 0
    if carry_roll <= 2:
        if random.randint(1, 6) <= 4:
            extra_scrolls = 1
        else:
            armor = ARMOR[6]
    else:
        combat_roll = random.randint(1, 12)
        personal_roll = random.randint(1, 12)
        gear.extend((COMBAT_GEAR[combat_roll - 1], PERSONAL_GEAR[personal_roll - 1]))
        if combat_roll == 12:
            extra_scrolls += 1
        if carry_roll + combat_roll + personal_roll >= 20:
            gear.append("Battle-hardened: +1 on the SHOCK table")

    scroll_count = _roll_war_scroll_count(template.war_scrolls) + extra_scrolls
    war_scrolls = random.sample(WAR_SCROLLS, min(scroll_count, len(WAR_SCROLLS)))
    nickname = name.strip() or random.choice(NICKNAMES)

    return FarewellCharacter(
        user_id=user_id, discord_name=discord_name, name=nickname,
        class_slug=template.slug, class_name=template.name,
        agility=stats["agility"], presence=stats["presence"], strength=stats["strength"], toughness=stats["toughness"],
        hp=hp, max_hp=hp, omens=omens, silver=silver, ammo=ammo, shock=shock, powers=powers,
        reason=random.choice(REASONS_FOR_ENLISTMENT), battle_scar=random.choice(BATTLE_SCARS), vice=random.choice(VICES),
        firearm=firearm, sidearm=sidearm, armor=armor, specialty=specialty,
        history=random.choice(template.histories) if template.histories else "", gear=gear,
        war_scrolls=war_scrolls, notes=template.notes,
    )
