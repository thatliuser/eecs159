{
  description = "A very basic flake";

  inputs = {
    nixpkgs.url = "nixpkgs";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
    in
    {
      packages."${system}" = rec {
        pen = pkgs.stdenv.mkDerivation {
          pname = "pen";
          version = "0.0.1";
          nativeBuildInputs = with pkgs; [
            (python3.withPackages (py: with py; [
              pyserial
              bleak
              matplotlib
              numpy
              pandas
              filterpy
              opencv4
            ]))
            arduino-cli
            tio
          ];
        };
        default = pen;
      };
    };
}

