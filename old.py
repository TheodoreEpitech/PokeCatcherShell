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
    def __init__(self, name, shiny=False, level=1):
        self.name = name
        self.shiny = shiny
        self.level = level
        self.id = pokemons.index(name) + 1
    
    def __str__(self):
        return self.name
    
    def spawn(self):
        if (randint(1, 100) > 100 - shiny_rate):
            self.shiny = True

        self.level = randint(1, max_lvl)

    def catch(self, team):
        if (randint(1, max_lvl) >= self.level / catch_rate):
            print("You caught a " + self.name + " !")
            team.append(self)
            caught = True
        else:
            print("You failed to catch the " + self.name + " :/")
            caught = False
        input("Press Enter to continue...")
        return caught

    def remove_from_team(self, team):
        if (self in team):
            team.remove(self)

    def show(self):
        print("ID: " + str(self.id))
        print("Shiny: " + str(self.shiny))
        print("LVL: \033[91m" + str(self.level) + "\033[0m")
        args_list = ['krabby', 'name', self.name, '-i']
        if (self.shiny):
            args_list.append("-s")
        subprocess.run(args_list)

    def dump(self):
        return {
            "name": self.name,
            "shiny": self.shiny,
            "level": self.level
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
                pokemon = Pokemon(pokedex[temp]["name"], pokedex[temp]["shiny"], pokedex[temp]["level"])
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
    
    pokedex = dict(sorted(pokedex.items()))
    with open("pokedex.json", "w") as file:
        json.dump(pokedex, file)
    return pokedex

#-------------------------
# Game Loop
#-------------------------
def get_action(pokemon, team, pokedex):
    clear_terminal()
    pokemon.show()
    temp = input("List of actions:\n- 1: Catch\n- 2: Continue\n- 3: Show Team\n- 4: Show Pokedex\n- 5: Exit\n")
    match temp:
        case ("1"):
            if pokemon.catch(team):
                pokedex = save_team_in_pokedex([pokemon], pokedex)
            return pokedex
        case ("2"):
            return pokedex
        case ("3"):
            show_team(team)
        case ("4"):
            show_pokedex(pokedex)
        case ("5"):
            exit()
        case _:
            print("Invalid action")
    return get_action(pokemon, team, pokedex)

#-------------------------
# Main
#-------------------------
def handle_sigint(signum, frame):
    print("Exiting...")
    exit(0)

def main():
    signal.signal(signal.SIGINT, handle_sigint)
    team = []
    try:
        pokedex = json.load(open("pokedex.json"))
    except:
        pokedex = {}

    while (len(team) < team_size):
        nb = randint(0, len(pokemons) - 1)
        pokemon = Pokemon(pokemons[nb])

        pokemon.spawn()

        pokedex = get_action(pokemon, team, pokedex)

    show_team(team)
    print("You have a full team !")
    pokedex = save_team_in_pokedex(team, pokedex)
    print("The team got added to the pokedex !")
    print("You now have " + str(len(pokedex)) + "/" + str(len(pokemons)) + " pokemons in your pokedex !")

if __name__ == "__main__":
    main()
