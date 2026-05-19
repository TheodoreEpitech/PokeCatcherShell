#-------------------------
# Imports
#-------------------------
import subprocess
from random import randint
import json
import signal

#-------------------------
# Config
#-------------------------
shiny_rate = 1
catch_rate = 1
team_size = 6
max_lvl = 100

try:
    with open("config.json", "r") as f:
        config_data = json.load(f)
        shiny_rate = config_data.get("shiny_rate", shiny_rate)
        catch_rate = config_data.get("catch_rate", catch_rate)
        team_size = config_data.get("team_size", team_size)
        max_lvl = config_data.get("max_lvl", max_lvl)
except Exception:
    pass

#-------------------------
# Check if Krabby is installed
#-------------------------
try:
    result = subprocess.run(['krabby', 'list'], stdout=subprocess.PIPE)
    pokemons = str(result.stdout).split("'")[1].split("\\n")
    pokemons.pop()
except:
    print("Error: Krabby not found")
    print("Install Krabby (https://github.com/yannjor/krabby) with : cargo install krabby")
    exit()

#-------------------------
# Pokemon Class
#-------------------------
class Pokemon():
    def __init__(self, name, shiny=False, level=1, xp=0, hp=None):
        self.name = name
        self.shiny = shiny
        self.level = level
        self.id = pokemons.index(name) + 1
        self.xp = xp
        self.xp_to_next_level = self.level * 10
        self.max_hp = self.level * 10 + 50
        if hp is None:
            self.hp = self.max_hp
        else:
            self.hp = hp
    
    def __str__(self):
        return self.name
    
    def spawn(self):
        if (randint(1, 100) > 100 - shiny_rate):
            self.shiny = True
        self.level = randint(1, max_lvl)
        self.xp = 0
        self.xp_to_next_level = self.level * 10
        self.max_hp = self.level * 10 + 50
        self.hp = self.max_hp

    def catch(self, team):
        # Scale catch rate based on HP percentage
        hp_ratio = self.hp / self.max_hp
        effective_level = max(1, int(self.level * hp_ratio))
        if (randint(1, max_lvl) >= effective_level / catch_rate):
            print("You caught a " + self.name + " !")
            team.append(self)
            caught = True
        else:
            print("You failed to catch the " + self.name + " :/")
            caught = False
        input("Press Enter to continue...")
        return caught

    def gain_xp(self, amount):
        if self.level >= max_lvl:
            return False
        self.xp += amount
        leveled_up = False
        while self.xp >= self.xp_to_next_level and self.level < max_lvl:
            self.xp -= self.xp_to_next_level
            self.level += 1
            self.xp_to_next_level = self.level * 10
            self.max_hp = self.level * 10 + 50
            self.hp = self.max_hp  # Fully heal on level up
            leveled_up = True
        return leveled_up

    def remove_from_team(self, team):
        if (self in team):
            team.remove(self)

    def show(self):
        print("ID: " + str(self.id))
        print("Shiny: " + str(self.shiny))
        print("LVL: \033[91m" + str(self.level) + "\033[0m")
        print(f"HP: \033[92m{self.hp}/{self.max_hp}\033[0m | XP: \033[94m{self.xp}/{self.xp_to_next_level}\033[0m")
        args_list = ['krabby', 'name', self.name, '-i']
        if (self.shiny):
            args_list.append("-s")
        subprocess.run(args_list)

    def dump(self):
        return {
            "name": self.name,
            "shiny": self.shiny,
            "level": self.level,
            "xp": self.xp,
            "hp": self.hp
        }

#-------------------------
# Tools
#-------------------------
def clear_terminal():
    subprocess.run("clear")

def show_team(team):
    clear_terminal()
    print("=============================================================")
    print("=============================================================")
    print("Your team:")
    for poke in team:
        poke.show()
    print("=============================================================")
    print("=============================================================")
    input("Press Enter to continue...")

def show_pokedex(pokedex):
    clear_terminal()
    print("=============================================================")
    print("=============================================================")
    print("Your pokedex:")
    for poke_id, poke in pokedex.items():
        print(str(poke_id) + " - " + poke["name"] + " - Level: \033[91m" + str(poke["level"]) + "\033[0m" + " - Shiny: " + str(poke["shiny"]))
    print("=============================================================")
    print("=============================================================")
    temp = input("List of actions:\n- 1: Continue\n- 2: Show Pokemon\n")
    match temp:
        case ("1"):
            return
        case ("2"):
            temp = input("Enter the ID of the pokemon you want to see: ")
            if (temp in pokedex):
                pokemon = Pokemon(
                    pokedex[temp]["name"], 
                    pokedex[temp]["shiny"], 
                    pokedex[temp]["level"],
                    pokedex[temp].get("xp", 0),
                    pokedex[temp].get("hp", None)
                )
                pokemon.show()
            else:
                print("Pokemon not found")
            input("Press Enter to continue...")
            show_pokedex(pokedex)
        case _:
            print("Invalid action")
            show_pokedex(pokedex)

def save_team_in_pokedex(team, pokedex):
    for poke in team:

        pokemon_id = str(poke.id)
        for _ in range(len(pokemon_id), 3):
            pokemon_id = "0" + pokemon_id

        if (pokemon_id not in pokedex):
            pokedex[pokemon_id] = poke.dump()
        elif (pokedex[pokemon_id]["level"] < poke.level and not pokedex[pokemon_id]["shiny"]):
            pokedex[pokemon_id] = poke.dump()
        elif (not pokedex[pokemon_id]["shiny"] and poke.shiny):
            pokedex[pokemon_id] = poke.dump()
        elif (pokedex[pokemon_id]["shiny"] and poke.shiny and pokedex[pokemon_id]["level"] < poke.level):
            pokedex[pokemon_id] = poke.dump()
    
    pokedex = dict(sorted(pokedex.items(), key=lambda item: int(item[0])))
    with open("pokedex.json", "w") as file:
        json.dump(pokedex, file)
    return pokedex

#-------------------------
# Game Loop
#-------------------------
def get_action(pokemon, team, pokedex):
    clear_terminal()
    pokemon.show()
    temp = input("List of actions:\n- 1: Catch\n- 2: Battle\n- 3: Continue\n- 4: Show Team\n- 5: Show Pokedex\n- 6: Heal Team\n- 7: Exit\n")
    match temp:
        case ("1"):
            if pokemon.catch(team):
                pokedex = save_team_in_pokedex([pokemon], pokedex)
            return pokedex
        case ("3"):
            return pokedex
        case ("4"):
            show_team(team)
        case ("5"):
            show_pokedex(pokedex)
        case ("7"):
            exit()
        case ("2"):
            active_member = None
            for member in team:
                if member.hp > 0:
                    active_member = member
                    break
            if not active_member:
                if len(team) == 0:
                    print("\033[91mYou don't have any Pokémon to battle with!\033[0m")
                else:
                    print("\033[91mAll your team members are fainted! Heal them first.\033[0m")
            else:
                print(f"\n\033[95mBATTLE START!\033[0m Go, {active_member.name.capitalize()}! (Lvl {active_member.level})")
                print(f"vs wild {pokemon.name.capitalize()} (Lvl {pokemon.level})\n")
                
                round_num = 1
                while active_member.hp > 0 and pokemon.hp > 1:
                    player_dmg = randint(int(active_member.level * 0.5) + 1, int(active_member.level * 1.5) + 3)
                    pokemon.hp = max(1, pokemon.hp - player_dmg)
                    print(f"R{round_num}: {active_member.name.capitalize()} dealt \033[92m{player_dmg} DMG\033[0m! (Wild HP: {pokemon.hp}/{pokemon.max_hp})")
                    
                    if pokemon.hp <= 1:
                        break
                        
                    wild_dmg = randint(int(pokemon.level * 0.5) + 1, int(pokemon.level * 1.5) + 3)
                    active_member.hp = max(0, active_member.hp - wild_dmg)
                    print(f"R{round_num}: Wild {pokemon.name.capitalize()} dealt \033[91m{wild_dmg} DMG\033[0m! ({active_member.name.capitalize()} HP: {active_member.hp}/{active_member.max_hp})")
                    
                    round_num += 1
                    if round_num > 5:
                        break
                        
                if pokemon.hp <= 1:
                    print(f"\n\033[92mVICTORY!\033[0m Wild {pokemon.name.capitalize()} is extremely weakened!")
                    xp_gained = pokemon.level * 3
                    leveled_up = active_member.gain_xp(xp_gained)
                    print(f"{active_member.name.capitalize()} gained \033[94m{xp_gained} XP\033[0m!")
                    if leveled_up:
                        print(f"🎉 \033[93mLEVEL UP!\033[0m {active_member.name.capitalize()} grew to \033[91mLevel {active_member.level}\033[0m!")
                elif active_member.hp == 0:
                    print(f"\n\033[91mDEFEAT!\033[0m {active_member.name.capitalize()} fainted!")
                else:
                    print(f"\nThe battle timed out! Wild {pokemon.name.capitalize()} is weakened.")
            input("\nPress Enter to continue...")
        case ("6"):
            healed = False
            for member in team:
                if member.hp < member.max_hp:
                    member.hp = member.max_hp
                    healed = True
            if healed:
                print("\033[92mYour team was fully healed!\033[0m")
                print("Skipping the current Pokémon...")
                input("\nPress Enter to continue...")
                return pokedex
            else:
                print("Your team is already at full health.")
                input("\nPress Enter to continue...")
        case _:
            print("Invalid action")
    return get_action(pokemon, team, pokedex)

def select_starter(pokedex):
    clear_terminal()
    print("=============================================================")
    print("★ CHOOSE YOUR STARTING PARTNER ★")
    print("=============================================================")
    
    # If pokedex is empty or they choose classic
    if not pokedex:
        print("Your PokéDex is empty! Select a classic Starter Pokémon to begin:\n")
        print("1. Bulbasaur (Lvl 5)")
        print("2. Charmander (Lvl 5)")
        print("3. Squirtle (Lvl 5)")
        choice = input("\nEnter choice (1-3): ")
        match choice:
            case "1": return Pokemon("bulbasaur", False, 5)
            case "2": return Pokemon("charmander", False, 5)
            case "3": return Pokemon("squirtle", False, 5)
            case _: return select_starter(pokedex)
    else:
        print("Select your starting partner:\n")
        print("--- Classic Starters ---")
        print("1. Bulbasaur (Lvl 5)")
        print("2. Charmander (Lvl 5)")
        print("3. Squirtle (Lvl 5)\n")
        
        print("--- From your PokéDex ---")
        poke_keys = list(pokedex.keys())
        for idx, poke_id in enumerate(poke_keys):
            poke_data = pokedex[poke_id]
            shiny_tag = " ✨" if poke_data["shiny"] else ""
            print(f"{idx + 4}. {poke_data['name'].capitalize()} (Lvl {poke_data['level']}){shiny_tag}")
            
        choice = input(f"\nEnter choice (1-{len(poke_keys) + 3}): ")
        try:
            val = int(choice)
            if val == 1:
                return Pokemon("bulbasaur", False, 5)
            elif val == 2:
                return Pokemon("charmander", False, 5)
            elif val == 3:
                return Pokemon("squirtle", False, 5)
            elif 4 <= val <= len(poke_keys) + 3:
                selected_key = poke_keys[val - 4]
                poke_data = pokedex[selected_key]
                return Pokemon(
                    poke_data["name"], 
                    poke_data["shiny"], 
                    poke_data["level"], 
                    poke_data.get("xp", 0)
                )
            else:
                return select_starter(pokedex)
        except ValueError:
            return select_starter(pokedex)

#-------------------------
# Main
#-------------------------
def handle_sigint(signum, frame):
    print("Exiting...")
    exit(0)

def main():
    signal.signal(signal.SIGINT, handle_sigint)
    try:
        pokedex = json.load(open("pokedex.json"))
    except:
        pokedex = {}

    while True:
        starter = select_starter(pokedex)
        team = [starter]
        pokedex = save_team_in_pokedex([starter], pokedex)
        print(f"\nSelected {starter.name.capitalize()} as your starting partner!\n")
        input("Press Enter to continue your journey...")

        game_lost = False
        while (len(team) < team_size):
            nb = randint(0, len(pokemons) - 1)
            pokemon = Pokemon(pokemons[nb])
            pokemon.spawn()

            pokedex = get_action(pokemon, team, pokedex)

            # Check if all team members fainted
            if len(team) > 0 and all(member.hp <= 0 for member in team):
                clear_terminal()
                print("=============================================================")
                print("\033[91m☠ GAME OVER ☠\033[0m")
                print("All your Pokémon have fainted!")
                print("Your journey has ended. Train hard, take care of your partner, and try again!")
                print("=============================================================")
                input("\nPress Enter to restart a new journey...")
                game_lost = True
                break

        if game_lost:
            continue

        show_team(team)
        print("You have a full team !")
        pokedex = save_team_in_pokedex(team, pokedex)
        print("The team got added to the pokedex !")
        print("You now have " + str(len(pokedex)) + "/" + str(len(pokemons)) + " pokemons in your pokedex !")
        break

if __name__ == "__main__":
    main()
