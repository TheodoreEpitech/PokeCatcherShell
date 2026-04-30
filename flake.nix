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
            python3
            krabby
          ];

          shellHook = ''
            echo "Welcome to PokeCatcherShell!"
            echo "Run 'python main.py' or './run.sh' to start catching pokemons."
          '';
        };
      }
    );
}
