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
        ahrs = pkgs.python3Packages.buildPythonPackage rec {
          name = "ahrs";
          version = "0.4.0";
          format = "pyproject";
          src = pkgs.fetchFromGitHub {
            owner = "Mayitzin";
            repo = "${name}";
            rev = "1933f72309909c770357182b19a966a08366dd32";
            sha256 = "RrnoMzeVidLaZEu9Z3MFVaGBykfELFVlyBlzMSLrZn0=";
          };

          propagatedBuildInputs = with pkgs.python3Packages; [ numpy hatchling docutils ];
        };
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
              self.outputs.packages."${system}".ahrs
            ]))
            arduino-cli
            tio
          ];
        };
        default = pen;
      };
    };
}

