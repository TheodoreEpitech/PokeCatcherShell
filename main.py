#-------------------------
# Imports
#-------------------------
import subprocess
from random import randint
import json
import signal
import os

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button, TabbedContent, TabPane, ListView, ListItem, Label, Log
from textual.containers import Grid, Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual import on
from rich.text import Text
from rich.panel import Panel

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
    pokemons = [p.strip() for p in result.stdout.decode('utf-8').split("\n") if p.strip()]
except Exception as e:
    # fallback
    try:
        raw_list = str(result.stdout).split("'")[1].split("\\n")
        pokemons = [p.replace('\\r', '').strip() for p in raw_list if p.strip()]
    except:
        print("Error: Krabby not found")
        print("Install Krabby (https://github.com/yannjor/krabby) with : cargo install krabby")
        exit(1)

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

    def roll_catch(self):
        # Scale catch rate based on HP percentage
        hp_ratio = self.hp / self.max_hp
        effective_level = max(1, int(self.level * hp_ratio))
        return (randint(1, max_lvl) >= effective_level / catch_rate)

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

    def get_sprite(self, include_info=False):
        args_list = ['krabby', 'name', self.name]
        if include_info:
            args_list.append('-i')
        else:
            args_list.append('--no-title')
            
        if self.shiny:
            args_list.append("-s")
        try:
            res = subprocess.run(args_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode != 0:
                return f"Error running krabby (code {res.returncode}):\n{res.stderr}\nStdout: {res.stdout}"
            return res.stdout
        except Exception as e:
            return f"Error loading sprite: {e}"

    def dump(self):
        return {
            "name": self.name,
            "shiny": self.shiny,
            "level": self.level,
            "xp": self.xp,
            "hp": self.hp
        }

#-------------------------
# Save/Load Pokedex Functions
#-------------------------
def load_pokedex():
    try:
        if os.path.exists("pokedex.json"):
            with open("pokedex.json", "r") as file:
                return json.load(file)
    except Exception:
        pass
    return {}

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
# Victory Screen (Modal Overlay)
#-------------------------
class VictoryScreen(Screen):
    def __init__(self, stat_text, **kwargs):
        super().__init__(**kwargs)
        self.stat_text = stat_text
        
    def compose(self) -> ComposeResult:
        with Vertical(classes="gameover-panel"):
            yield Static("★ CONGRATULATIONS! ★", classes="gameover-title")
            yield Static("Your team is full (6 Pokemons)!", classes="gameover-subtitle")
            yield Static(self.stat_text, id="gameover-stats")
            yield Button("START A NEW JOURNEY", id="btn-restart", classes="restart-btn")
            
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-restart":
            event.button.disabled = True
            self.dismiss(result="restart")

#-------------------------
# Game Over Screen
#-------------------------
class GameOverScreen(Screen):
    def compose(self) -> ComposeResult:
        with Vertical(classes="gameover-panel fainted-panel"):
            yield Static("☠ GAME OVER ☠", classes="gameover-title fainted-title")
            yield Static("All your Pokémon have fainted!", classes="gameover-subtitle")
            yield Static("Your journey has ended. Train hard, take care of your partner, and try again!", id="gameover-stats")
            yield Button("RETRY / NEW JOURNEY", id="btn-restart", classes="restart-btn retry-btn")
            
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-restart":
            event.button.disabled = True
            self.dismiss(result="restart")

#-------------------------
# Starter Choice Screen
#-------------------------
class StarterScreen(Screen):
    def __init__(self, pokedex, **kwargs):
        super().__init__(**kwargs)
        self.pokedex = pokedex
        self.partner_selected = False
        
    def compose(self) -> ComposeResult:
        with Vertical(classes="starter-panel"):
            yield Static("★ CHOOSE YOUR PARTNER ★", classes="starter-title")
            
            if not self.pokedex:
                yield Static("Your PokéDex is empty! Select a classic Starter Pokémon to begin:", classes="starter-subtitle")
                with Horizontal(classes="starter-cards"):
                    yield Button("Bulbasaur (Lvl 5)", id="starter-bulbasaur", classes="starter-card-btn")
                    yield Button("Charmander (Lvl 5)", id="starter-charmander", classes="starter-card-btn")
                    yield Button("Squirtle (Lvl 5)", id="starter-squirtle", classes="starter-card-btn")
            else:
                yield Static("Select your starting partner from your PokéDex or choice of classic starters:", classes="starter-subtitle")
                with Horizontal(classes="starter-choice-container"):
                    with Vertical(classes="classic-starters-column"):
                        yield Static("Classic Starters:", classes="column-title")
                        yield Button("Bulbasaur (Lvl 5)", id="starter-bulbasaur", classes="starter-card-btn")
                        yield Button("Charmander (Lvl 5)", id="starter-charmander", classes="starter-card-btn")
                        yield Button("Squirtle (Lvl 5)", id="starter-squirtle", classes="starter-card-btn")
                    with Vertical(classes="pokedex-starters-column"):
                        yield Static("From your PokéDex:", classes="column-title")
                        yield ListView(id="starter-pokedex-list")
                        
    def on_mount(self) -> None:
        if self.pokedex:
            pokedex_list = self.query_one("#starter-pokedex-list")
            for poke_id, poke in self.pokedex.items():
                shiny_tag = " ✨" if poke["shiny"] else ""
                label_text = f"{poke_id} - {poke['name'].capitalize()} (Lvl {poke['level']}){shiny_tag}"
                item = ListItem(Label(label_text))
                item.poke_data = poke
                pokedex_list.append(item)
                
    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.button.disabled = True
        button_id = event.button.id
        if button_id == "starter-bulbasaur":
            self.select_partner(Pokemon("bulbasaur", level=5))
        elif button_id == "starter-charmander":
            self.select_partner(Pokemon("charmander", level=5))
        elif button_id == "starter-squirtle":
            self.select_partner(Pokemon("squirtle", level=5))
            
    @on(ListView.Selected)
    def handle_pokedex_selected(self, event: ListView.Selected) -> None:
        if not event.item or not getattr(event.item, "poke_data", None):
            return
        poke_data = event.item.poke_data
        partner = Pokemon(
            poke_data["name"], 
            poke_data["shiny"], 
            poke_data["level"], 
            poke_data.get("xp", 0)
        )
        self.select_partner(partner)
        
    def select_partner(self, pokemon) -> None:
        if self.partner_selected:
            return
        self.partner_selected = True
        self.app.set_starting_partner(pokemon)
        self.dismiss()

#-------------------------
# TUI App
#-------------------------
class PokeCatcherApp(App):
    TITLE = "PokeCatcher TUI"
    SUB_TITLE = "Catch 'em all in style!"
    
    # Custom vibrant CSS with rich animations and professional design
    CSS = """
    Screen {
        background: #0d0e15;
        color: #c5cdd8;
    }
    
    Header {
        background: #161925;
        color: #00ffaa;
        text-style: bold;
        border-bottom: solid #00ffaa;
    }
    
    Footer {
        background: #161925;
        color: #8f9bb3;
    }
    
    TabbedContent {
        background: #0f111a;
    }
    
    TabPane {
        background: #0f111a;
        padding: 1 2;
    }
    
    Tabs {
        background: #161925;
        border-bottom: solid #2c3144;
    }
    
    Tab {
        color: #8f9bb3;
    }
    
    Tab:hover {
        background: #202436;
        color: #ffffff;
    }
    
    Tab.-active {
        background: #0f111a;
        color: #00ffaa;
        text-style: bold;
    }
    
    /* Catch Area Styles */
    .catch-layout {
        layout: horizontal;
        height: 38;
    }
    
    .catch-control-panel {
        width: 35%;
        height: 100%;
        background: #161925;
        border: round #00ffaa;
        padding: 1 2;
        align: center middle;
    }
    
    .combatants-panel {
        width: 65%;
        height: 100%;
        background: #08090f;
        border: round #2c3144;
        layout: horizontal;
    }

    .combatant-subpanel {
        width: 50%;
        height: 100%;
        padding: 1;
        align: center middle;
    }

    .wild-subpanel {
        border-right: solid #1c2134;
    }

    .combatant-header {
        text-style: bold;
        color: #ff5555;
        text-align: center;
        margin-bottom: 1;
    }

    .active-subpanel .combatant-header {
        color: #00ffaa;
    }

    .combatant-sprite {
        height: 22;
        width: 100%;
        content-align: center middle;
        overflow: hidden;
        margin-bottom: 1;
    }

    .combatant-details {
        text-align: center;
        color: #ffffff;
        text-style: bold;
    }
    
    .shiny-glow {
        color: #ff00ff;
        text-style: bold blink;
    }
    
    .catch-buttons {
        layout: vertical;
        height: auto;
        align: center middle;
        margin: 1 0;
    }
    
    .catch-buttons Button {
        margin: 1 0;
        width: 100%;
        height: 3;
    }
    
    #btn-catch {
        background: #008855;
        color: white;
        text-style: bold;
        border: tall #00ffaa;
    }
    
    #btn-catch:hover {
        background: #00aa66;
    }
    
    #btn-run {
        background: #880033;
        color: white;
        text-style: bold;
        border: tall #ff0055;
    }
    
    #btn-run:hover {
        background: #aa0044;
    }
    
    .status-panel {
        height: 14;
        overflow-y: scroll;
        background: #11121d;
        border: solid #2c3144;
        padding: 0 1;
        text-align: left;
        text-style: bold;
        color: #ffcc00;
    }
    
    /* Team Area Styles */
    .team-header-title {
        color: #ffcc00;
        text-style: bold;
        text-align: center;
        background: #161925;
        border: solid #2c3144;
        padding: 1;
        width: 100%;
        margin-bottom: 1;
    }
    
    #team-scroll-container {
        height: 1fr;
        overflow-y: auto;
    }
    
    .team-grid {
        grid-size: 3 2;
        grid-gutter: 1 2;
        grid-rows: 30;
        height: 63;
    }
    
    .team-slot {
        background: #131522;
        border: round #2c3144;
        padding: 1;
        align: center middle;
        height: 100%;
    }
    
    .team-slot.filled {
        background: #1a1e2f;
        border: round #ffcc00;
    }
    
    .team-slot.shiny-pokemon {
        background: #25162f;
        border: round #ff00ff;
    }
    
    .team-slot-sprite {
        height: 22;
        width: 100%;
        content-align: center middle;
        overflow: hidden;
        margin-bottom: 1;
    }
    
    .slot-name {
        text-style: bold;
        color: #ffffff;
        text-align: center;
    }
    
    .slot-details {
        color: #8f9bb3;
        text-align: center;
        margin-bottom: 1;
    }
    
    .release-btn {
        background: #cc3333;
        color: white;
        border: none;
        width: 16;
        height: 3;
    }
    
    .release-btn:hover {
        background: #ff5555;
    }
    
    VictoryScreen {
        align: center middle;
        background: rgba(13, 14, 21, 0.95);
    }
    
    VictoryScreen .gameover-panel {
        background: #161925;
        border: round #00ffaa;
        padding: 2 4;
        align: center middle;
        width: 80%;
        height: auto;
    }
    
    VictoryScreen .gameover-title {
        color: #ff00ff;
        text-style: bold blink;
        text-align: center;
        margin-bottom: 1;
    }
    
    VictoryScreen .gameover-subtitle {
        color: #ffcc00;
        text-align: center;
        margin-bottom: 2;
    }
    
    VictoryScreen .restart-btn {
        background: #00ffaa;
        color: #0d0e15;
        text-style: bold;
        height: 3;
        width: 30;
        margin-top: 1;
    }
    
    /* Pokedex Area Styles */
    .pokedex-layout {
        layout: horizontal;
        height: 30;
    }
    
    .pokedex-list-panel {
        width: 30%;
        height: 100%;
        background: #161925;
        border: round #2c3144;
        padding: 1;
    }
    
    .pokedex-detail-panel {
        width: 70%;
        height: 100%;
        background: #08090f;
        border: round #00ffaa;
        padding: 1 2;
        margin-left: 1;
        overflow: auto;
    }
    
    .pokedex-list-widget {
        background: transparent;
    }
    
    .pokedex-item-label {
        color: #c5cdd8;
        padding: 0 1;
    }
    
    .pokedex-item-label.-selected {
        background: #00ffaa;
        color: #0d0e15;
        text-style: bold;
    }
    
    .completion-bar {
        background: #161925;
        border: solid #2c3144;
        padding: 0 1;
        margin-top: 1;
        height: 3;
        align: center middle;
        color: #00ffaa;
        text-style: bold;
    }
    
    /* Game Over Panel */
    .gameover-container {
        align: center middle;
        height: 100%;
        layout: vertical;
    }
    
    .gameover-panel {
        background: #1f1425;
        border: double #ff00ff;
        padding: 2 4;
        align: center middle;
        width: 80%;
        height: auto;
    }
    
    .gameover-title {
        color: #ff00ff;
        text-style: bold blink;
        text-align: center;
        margin-bottom: 1;
    }
    
    .gameover-subtitle {
        color: #ffcc00;
        text-align: center;
        margin-bottom: 2;
    }
    
    .restart-btn {
        background: #00ffaa;
        color: #0d0e15;
        text-style: bold;
        height: 3;
    }
    
    #btn-battle {
        background: #3a0088;
        color: white;
        text-style: bold;
        border: tall #8800ff;
    }
    
    #btn-battle:hover {
        background: #5a00aa;
    }

    .team-header-layout {
        height: 5;
        margin-bottom: 1;
        align: center middle;
    }
    
    #team-header-title {
        width: 70%;
        height: 100%;
        color: #ffcc00;
        text-style: bold;
        text-align: center;
        background: #161925;
        border: solid #2c3144;
        padding: 1 0;
        margin: 0;
    }

    .heal-team-btn {
        width: 30%;
        height: 100%;
        background: #008855;
        color: white;
        border: solid #00ffaa;
        text-style: bold;
        margin: 0 0 0 1;
    }

    .heal-team-btn:hover {
        background: #00aa66;
    }

    .slot-stat-label {
        text-align: center;
        margin-bottom: 0;
        color: #8f9bb3;
    }

    .team-slot.fainted {
        background: #141419;
        border: round #555555;
    }

    .team-slot.fainted .slot-name {
        color: #555555;
        text-style: strike;
    }

    StarterScreen {
        align: center middle;
        background: rgba(13, 14, 21, 0.95);
    }
    
    StarterScreen .starter-panel {
        background: #161925;
        border: round #00ffaa;
        padding: 2 4;
        align: center middle;
        width: 80%;
        height: auto;
        max-height: 28;
    }
    
    StarterScreen .starter-title {
        color: #ffcc00;
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }
    
    StarterScreen .starter-subtitle {
        color: #c5cdd8;
        text-align: center;
        margin-bottom: 2;
    }

    .starter-cards {
        layout: horizontal;
        height: 5;
        align: center middle;
    }

    .starter-card-btn {
        margin: 0 1;
        width: 25;
        height: 3;
        background: #1f2335;
        color: #00ffaa;
        border: tall #00ffaa;
    }

    .starter-card-btn:hover {
        background: #2a304b;
    }

    .starter-choice-container {
        layout: horizontal;
        height: 16;
    }

    .classic-starters-column {
        width: 40%;
        height: 100%;
        align: center middle;
    }

    .classic-starters-column Button {
        margin: 1 0;
        width: 100%;
    }

    .pokedex-starters-column {
        width: 60%;
        height: 100%;
        margin-left: 2;
        border-left: solid #2c3144;
        padding-left: 2;
    }

    #starter-pokedex-list {
        background: #0d0e15;
        border: solid #2c3144;
        height: 12;
        overflow-y: auto;
    }

    .column-title {
        text-style: bold;
        margin-bottom: 1;
        color: #ffffff;
    }

    .fainted-panel {
        border: round #ff5555;
    }
    
    .fainted-title {
        color: #ff5555;
    }
    
    .retry-btn {
        background: #331f23;
        color: #ff5555;
        border: tall #ff5555;
    }
    
    .retry-btn:hover {
        background: #4d2b31;
    }
    """
    
    # BINDINGS
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("c", "catch", "Catch"),
        ("b", "battle", "Battle"),
        ("r", "run", "Run/Next"),
        ("h", "heal", "Heal Team"),
    ]
    
    # State reactive properties
    game_over = reactive(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.team = []
        self.pokedex = load_pokedex()
        self.current_pokemon = None
        
    def compose(self) -> ComposeResult:
        yield Header()
        
        with TabbedContent(id="tabs"):
            with TabPane("Catch Pokemon", id="tab-catch"):
                with Horizontal(id="catching-view", classes="catch-layout"):
                    with Vertical(classes="catch-control-panel"):
                        yield Static("POKEMON DETECTED", id="spawn-header", classes="slot-name")
                        yield Static("", id="spawn-name-label", classes="slot-name")
                        yield Static("", id="spawn-id-label")
                        yield Static("", id="spawn-level-label")
                        yield Static("", id="spawn-shiny-label")
                        
                        with Vertical(classes="catch-buttons"):
                            yield Button("CATCH (C)", id="btn-catch")
                            yield Button("BATTLE (B)", id="btn-battle")
                            yield Button("RUN / NEXT (R)", id="btn-run")
                            
                        yield Static("Ready to start catching!", id="status-display", classes="status-panel")
                    
                    with Horizontal(classes="combatants-panel"):
                        with Vertical(classes="combatant-subpanel wild-subpanel"):
                            yield Static("WILD POKEMON", classes="combatant-header")
                            yield Static("", id="wild-sprite", classes="combatant-sprite")
                            yield Static("", id="wild-details", classes="combatant-details")
                        with Vertical(classes="combatant-subpanel active-subpanel"):
                            yield Static("YOUR ACTIVE PARTNER", classes="combatant-header")
                            yield Static("", id="active-sprite", classes="combatant-sprite")
                            yield Static("", id="active-details", classes="combatant-details")
                            
            with TabPane("My Team", id="tab-team"):
                with Horizontal(classes="team-header-layout"):
                    yield Static("YOUR POKEMON TEAM (Max 6)", classes="team-header-title", id="team-header-title")
                    yield Button("HEAL TEAM (H)", id="btn-heal-team", classes="heal-team-btn")
                with ScrollableContainer(id="team-scroll-container"):
                    with Grid(id="team-grid", classes="team-grid"):
                        for i in range(6):
                            with Vertical(id=f"slot-{i}", classes="team-slot"):
                                yield Static("", id=f"slot-sprite-{i}", classes="team-slot-sprite")
                                yield Static("Empty Slot", id=f"slot-name-{i}", classes="slot-name")
                                yield Static("-", id=f"slot-details-{i}", classes="slot-details")
                                yield Static("", id=f"slot-hp-{i}", classes="slot-stat-label")
                                yield Static("", id=f"slot-xp-{i}", classes="slot-stat-label")
                                yield Button("Release", id=f"btn-release-{i}", classes="release-btn")
                            
            with TabPane("Pokedex", id="tab-pokedex"):
                with Horizontal(classes="pokedex-layout"):
                    with Vertical(classes="pokedex-list-panel"):
                        yield Static("List of Registered Pokemon:")
                        yield ListView(id="pokedex-list", classes="pokedex-list-widget")
                    
                    yield Static("Select a pokemon to view details", id="pokedex-detail-view", classes="pokedex-detail-panel")
                        
                yield Static("", id="completion-status", classes="completion-bar")
                
        yield Footer()

    def on_mount(self) -> None:
        self.spawn_new_pokemon()
        self.update_team_view()
        self.update_pokedex_view()
        self.push_screen(StarterScreen(self.pokedex))

    def spawn_new_pokemon(self) -> None:
        if self.game_over:
            return
            
        nb = randint(0, len(pokemons) - 1)
        self.current_pokemon = Pokemon(pokemons[nb])
        self.current_pokemon.spawn()
        
        # Update spawned Pokemon panel
        self.query_one("#spawn-name-label").update(f"Name: [b][yellow]{self.current_pokemon.name.capitalize()}[/yellow][/b]")
        self.query_one("#spawn-id-label").update(f"ID: {self.current_pokemon.id}")
        self.query_one("#spawn-level-label").update(f"Level: [bold red]{self.current_pokemon.level}[/bold red]")
        
        if self.current_pokemon.shiny:
            self.query_one("#spawn-shiny-label").update(Text("✨ SHINY ✨", style="bold #ff00ff blink"))
        else:
            self.query_one("#spawn-shiny-label").update("Normal")
            
        # Update wild combatant
        self.query_one("#wild-sprite").update(Text.from_ansi(self.current_pokemon.get_sprite(include_info=False)))
        
        wild_shiny_tag = " ✨" if self.current_pokemon.shiny else ""
        wild_hp_bar = self.make_bar(self.current_pokemon.hp, self.current_pokemon.max_hp)
        self.query_one("#wild-details").update(
            f"{self.current_pokemon.name.capitalize()} (Lvl {self.current_pokemon.level}){wild_shiny_tag}\nHP: {self.current_pokemon.hp}/{self.current_pokemon.max_hp} [{wild_hp_bar}]"
        )

    def action_catch(self) -> None:
        if self.game_over or len(self.team) >= team_size:
            return
            
        pokemon = self.current_pokemon
        if not pokemon:
            return
            
        success = pokemon.roll_catch()
        if success:
            self.team.append(pokemon)
            self.notify(f"You caught {pokemon.name.capitalize()}!", severity="information", title="Success!")
            self.query_one("#status-display").update(f"Successfully caught {pokemon.name.capitalize()} (Lvl {pokemon.level})!")
            self.update_team_view()
            
            # Save to pokedex immediately in real-time
            self.pokedex = save_team_in_pokedex([pokemon], self.pokedex)
            self.update_pokedex_view()
            
            # Check game over (team of 6)
            if len(self.team) >= team_size:
                self.trigger_game_over()
            else:
                self.spawn_new_pokemon()
        else:
            self.notify(f"Failed to catch {pokemon.name.capitalize()}! It ran away.", severity="warning", title="Missed!")
            self.query_one("#status-display").update(f"Failed to catch {pokemon.name.capitalize()} :/")
            self.spawn_new_pokemon()

    def action_run(self) -> None:
        if self.game_over:
            return
            
        pokemon = self.current_pokemon
        if pokemon:
            self.query_one("#status-display").update(f"You ran away from {pokemon.name.capitalize()}.")
            self.notify(f"Fled from {pokemon.name.capitalize()}", severity="normal")
            
        self.spawn_new_pokemon()

    def trigger_game_over(self) -> None:
        self.game_over = True
        
        # Save to pokedex
        self.pokedex = save_team_in_pokedex(self.team, self.pokedex)
        
        # Build victory screen stats
        stat_text = f"Congratulations! You've formed a full team of {team_size} Pokemons!\n\n"
        stat_text += "Your final team:\n"
        for i, poke in enumerate(self.team):
            shiny_tag = "✨ Shiny ✨ " if poke.shiny else ""
            stat_text += f"{i+1}. {poke.name.capitalize()} - Level {poke.level} {shiny_tag}\n"
            
        stat_text += f"\nThe team got added to the pokedex!\n"
        stat_text += f"You now have {len(self.pokedex)} / {len(pokemons)} pokemons in your pokedex ({len(self.pokedex)/len(pokemons)*100:.1f}% completion)!"
        
        self.update_pokedex_view()
        
        def check_restart(result):
            if result == "restart":
                self.set_timer(0.05, self.restart_journey)
                
        self.push_screen(VictoryScreen(stat_text), check_restart)


    def restart_journey(self) -> None:
        self.team = []
        self.game_over = False
        self.query_one("#status-display").update("A new journey begins! Good luck!")
        self.update_team_view()
        self.spawn_new_pokemon()
        self.push_screen(StarterScreen(self.pokedex))

    def set_starting_partner(self, pokemon: Pokemon) -> None:
        self.team = [pokemon]
        self.notify(f"Selected {pokemon.name.capitalize()} as your starting partner!", severity="information")
        self.update_team_view()
        self.pokedex = save_team_in_pokedex([pokemon], self.pokedex)
        self.update_pokedex_view()

    def make_bar(self, current, maximum, filled_char="█", empty_char="░", width=10) -> str:
        if maximum <= 0:
            return ""
        ratio = max(0.0, min(1.0, current / maximum))
        filled_count = int(ratio * width)
        empty_count = width - filled_count
        return filled_char * filled_count + empty_char * empty_count

    def update_team_view(self) -> None:
        for i in range(6):
            slot_card = self.query_one(f"#slot-{i}")
            slot_sprite = self.query_one(f"#slot-sprite-{i}")
            slot_name = self.query_one(f"#slot-name-{i}")
            slot_details = self.query_one(f"#slot-details-{i}")
            slot_hp = self.query_one(f"#slot-hp-{i}")
            slot_xp = self.query_one(f"#slot-xp-{i}")
            release_btn = self.query_one(f"#btn-release-{i}")
            
            if i < len(self.team):
                poke = self.team[i]
                slot_name.update(f"{poke.name.capitalize()}")
                shiny_tag = " [bold magenta]✨ Shiny ✨[/bold magenta]" if poke.shiny else ""
                
                if poke.hp == 0:
                    status_lbl = " [bold red][FAINTED][/bold red]"
                else:
                    status_lbl = ""
                
                slot_details.update(f"ID: {poke.id} | Lvl [bold red]{poke.level}[/bold red]{shiny_tag}{status_lbl}")
                
                # HP Bar
                hp_bar = self.make_bar(poke.hp, poke.max_hp)
                slot_hp.update(f"HP: {poke.hp}/{poke.max_hp} [{hp_bar}]")
                slot_hp.styles.display = "block"
                
                # XP Bar
                xp_bar = self.make_bar(poke.xp, poke.xp_to_next_level)
                slot_xp.update(f"XP: {poke.xp}/{poke.xp_to_next_level} [{xp_bar}]")
                slot_xp.styles.display = "block"
                
                # Fetch sprite without title/info
                sprite_ansi = poke.get_sprite(include_info=False)
                slot_sprite.update(Text.from_ansi(sprite_ansi))
                slot_sprite.styles.display = "block"
                
                release_btn.styles.display = "block"
                
                # Dynamic style classes
                slot_card.remove_class("filled", "shiny-pokemon", "fainted")
                slot_card.add_class("filled")
                if poke.shiny:
                    slot_card.add_class("shiny-pokemon")
                if poke.hp == 0:
                    slot_card.add_class("fainted")
            else:
                slot_name.update("Empty Slot")
                slot_details.update("-")
                slot_hp.update("")
                slot_hp.styles.display = "none"
                slot_xp.update("")
                slot_xp.styles.display = "none"
                slot_sprite.update("")
                slot_sprite.styles.display = "none"
                release_btn.styles.display = "none"
                slot_card.remove_class("filled", "shiny-pokemon", "fainted")

        self.update_active_combatant_display()

    def update_active_combatant_display(self) -> None:
        active_member = None
        for member in self.team:
            if member.hp > 0:
                active_member = member
                break
        if not active_member and len(self.team) > 0:
            active_member = self.team[0]
            
        if active_member:
            self.query_one("#active-sprite").update(Text.from_ansi(active_member.get_sprite(include_info=False)))
            active_shiny_tag = " ✨" if active_member.shiny else ""
            active_hp_bar = self.make_bar(active_member.hp, active_member.max_hp)
            status_lbl = " [bold red][FAINTED][/bold red]" if active_member.hp == 0 else ""
            self.query_one("#active-details").update(
                f"{active_member.name.capitalize()} (Lvl {active_member.level}){active_shiny_tag}{status_lbl}\nHP: {active_member.hp}/{active_member.max_hp} [{active_hp_bar}]"
            )
        else:
            self.query_one("#active-sprite").update("")
            self.query_one("#active-details").update("No Active Pokémon\nSelect partner first")

    def action_battle(self) -> None:
        if self.game_over:
            return
            
        wild_poke = self.current_pokemon
        if not wild_poke:
            return
            
        # Get first non-fainted team member
        active_member = None
        for member in self.team:
            if member.hp > 0:
                active_member = member
                break
                
        if not active_member:
            if len(self.team) == 0:
                self.notify("You have no Pokémon in your team to battle!", severity="error")
                self.query_one("#status-display").update("[bold red]No team members to battle! Catch one first.[/bold red]")
            else:
                self.notify("All your Pokémon are fainted! Heal them first.", severity="error")
                self.query_one("#status-display").update("[bold red]All your team members are fainted! Use Heal (H).[/bold red]")
            return

        # Start simulated battle
        battle_log = []
        battle_log.append(f"[bold magenta]BATTLE START![/bold magenta] Go, [yellow]{active_member.name.capitalize()}[/yellow]! (Lvl {active_member.level})")
        battle_log.append(f"vs wild [red]{wild_poke.name.capitalize()}[/red] (Lvl {wild_poke.level})")
        
        # Turn-based loop
        round_num = 1
        while active_member.hp > 0 and wild_poke.hp > 1:  # Weaken to at least 1 HP
            # Player attacks
            player_dmg = randint(int(active_member.level * 0.5) + 1, int(active_member.level * 1.5) + 3)
            wild_poke.hp = max(1, wild_poke.hp - player_dmg)
            battle_log.append(f"R{round_num}: {active_member.name.capitalize()} dealt [green]{player_dmg} DMG[/green]! (Wild HP: {wild_poke.hp}/{wild_poke.max_hp})")
            
            if wild_poke.hp <= 1:
                break
                
            # Wild attacks back
            wild_dmg = randint(int(wild_poke.level * 0.5) + 1, int(wild_poke.level * 1.5) + 3)
            active_member.hp = max(0, active_member.hp - wild_dmg)
            battle_log.append(f"R{round_num}: Wild {wild_poke.name.capitalize()} dealt [red]{wild_dmg} DMG[/red]! ({active_member.name.capitalize()} HP: {active_member.hp}/{active_member.max_hp})")
            
            round_num += 1
            if round_num > 5:
                break
                
        # Resolve battle
        if wild_poke.hp <= 1:
            battle_log.append(f"[bold green]VICTORY![/bold green] Wild {wild_poke.name.capitalize()} is extremely weakened!")
            xp_gained = wild_poke.level * 3
            leveled_up = active_member.gain_xp(xp_gained)
            battle_log.append(f"{active_member.name.capitalize()} gained [blue]{xp_gained} XP[/blue]!")
            if leveled_up:
                battle_log.append(f"🎉 [bold yellow]LEVEL UP![/bold yellow] {active_member.name.capitalize()} grew to [bold red]Level {active_member.level}[/bold red]!")
                self.notify(f"{active_member.name.capitalize()} leveled up to {active_member.level}!", severity="information")
        elif active_member.hp == 0:
            battle_log.append(f"[bold red]DEFEAT![/bold red] {active_member.name.capitalize()} fainted!")
            self.notify(f"{active_member.name.capitalize()} fainted!", severity="warning")
            
            # Check if all fainted
            all_fainted = all(member.hp <= 0 for member in self.team)
            if all_fainted:
                self.game_over = True
                def check_restart(result):
                    if result == "restart":
                        self.set_timer(0.05, self.restart_journey)
                self.push_screen(GameOverScreen(), check_restart)
        else:
            battle_log.append(f"The battle timed out! Wild {wild_poke.name.capitalize()} is weakened.")

        # Update displays
        self.query_one("#status-display").update("\n".join(battle_log))
        self.query_one("#spawn-level-label").update(f"Level: [bold red]{wild_poke.level}[/bold red] (HP: {wild_poke.hp}/{wild_poke.max_hp})")
        
        wild_shiny_tag = " ✨" if wild_poke.shiny else ""
        wild_hp_bar = self.make_bar(wild_poke.hp, wild_poke.max_hp)
        self.query_one("#wild-details").update(
            f"{wild_poke.name.capitalize()} (Lvl {wild_poke.level}){wild_shiny_tag}\nHP: {wild_poke.hp}/{wild_poke.max_hp} [{wild_hp_bar}]"
        )
        
        self.update_team_view()

    def heal_team(self) -> None:
        if self.game_over:
            return
            
        healed_any = False
        for member in self.team:
            if member.hp < member.max_hp:
                member.hp = member.max_hp
                healed_any = True
                
        if healed_any:
            self.notify("Your team was fully healed! Spawning a new wild Pokémon...", severity="information")
            self.query_one("#status-display").update("[bold green]Your team was fully healed! Spawning a new wild Pokémon...[/bold green]")
            self.update_team_view()
            self.spawn_new_pokemon()
        else:
            self.notify("Your team is already at full health.", severity="normal")

    def action_heal(self) -> None:
        self.heal_team()

    def update_pokedex_view(self) -> None:
        pokedex_list = self.query_one("#pokedex-list")
        pokedex_list.clear()
        
        for poke_id, poke in self.pokedex.items():
            shiny_tag = " ✨" if poke["shiny"] else ""
            label_text = f"{poke_id} - {poke['name'].capitalize()} (Lvl {poke['level']}){shiny_tag}"
            item = ListItem(Label(label_text))
            item.poke_id = poke_id
            pokedex_list.append(item)
            
        # Completion Bar
        comp_percent = (len(self.pokedex) / len(pokemons)) * 100
        self.query_one("#completion-status").update(
            f"Pokedex Completion: {len(self.pokedex)} / {len(pokemons)} ({comp_percent:.1f}%)"
        )

    def release_pokemon(self, index: int) -> None:
        if index < len(self.team):
            released = self.team.pop(index)
            self.notify(f"Released {released.name.capitalize()}", severity="warning")
            self.query_one("#status-display").update(f"Released {released.name.capitalize()} from team.")
            self.update_team_view()

    # Event handlers
    @on(Button.Pressed)
    def handle_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn-catch":
            self.action_catch()
        elif button_id == "btn-battle":
            self.action_battle()
        elif button_id == "btn-run":
            self.action_run()
        elif button_id == "btn-heal-team":
            self.heal_team()
        elif button_id == "btn-restart":
            self.restart_journey()
        elif button_id and button_id.startswith("btn-release-"):
            index = int(button_id.split("-")[-1])
            self.release_pokemon(index)

    @on(ListView.Selected)
    def handle_pokedex_selected(self, event: ListView.Selected) -> None:
        if not event.item or not getattr(event.item, "poke_id", None):
            return
            
        poke_id = event.item.poke_id
        if poke_id in self.pokedex:
            poke_data = self.pokedex[poke_id]
            # Create a temporary Pokemon to load sprite and info
            temp_poke = Pokemon(
                poke_data["name"], 
                poke_data["shiny"], 
                poke_data["level"], 
                poke_data.get("xp", 0), 
                poke_data.get("hp", None)
            )
            sprite_ansi = temp_poke.get_sprite(include_info=True)
            
            self.query_one("#pokedex-detail-view").update(Text.from_ansi(sprite_ansi))

#-------------------------
# Entry Point
#-------------------------
def main():
    app = PokeCatcherApp()
    app.run()

if __name__ == "__main__":
    main()
