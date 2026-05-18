{
  description = "A simple pokemon catcher shell game";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            (python3.withPackages (ps: with ps; [
              textual
            ]))
            krabby
          ];

          shellHook = ''
            echo "Welcome to PokeCatcherShell!"
            echo "Run 'python main.py' or 'python tui.py' to start catching pokemons."
          '';
        };
      }
    );
}
