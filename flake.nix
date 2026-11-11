{
  description = "Claude Code vs nanocode on Terminal-Bench 2.1: pinned tools";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      # The official nanocode release binary, as `curl https://nanocode.xyz/install | sh`
      # installs it (rolling `nanocode-cli` release, build of 2026-11-06, commit d7a4990).
      nanocode = pkgs.stdenvNoCC.mkDerivation {
        pname = "nanocode";
        version = "0.7.0-d7a4990";
        src = pkgs.fetchurl {
          url = "https://github.com/nanocodexyz/nanocode/releases/download/nanocode-cli/nanocode-x86_64-unknown-linux-gnu.gz";
          sha256 = "a5305c5a052d424d331a6d558c7d7820a0af1ef1c94c27a1c2f1682598bd7754";
        };
        dontUnpack = true;
        installPhase = ''
          mkdir -p $out/bin
          gunzip -c $src > $out/bin/nanocode
          chmod 755 $out/bin/nanocode
        '';
      };
    in
    {
      packages.${system} = { inherit nanocode; default = nanocode; };
      # Host-side tools. Harbor itself is pinned by uv.lock and installed in the VM;
      # Claude Code is pinned by version in scripts/make_job.py and installed per trial.
      devShells.${system}.default = pkgs.mkShell {
        packages = [ pkgs.python312 pkgs.uv pkgs.jq pkgs.zstd pkgs.git ];
        shellHook = ''
          # a copy, not a symlink: the benchmark VM mounts the repo but not /nix/store
          mkdir -p vendor
          install -m 755 ${nanocode}/bin/nanocode vendor/nanocode
        '';
      };
    };
}
