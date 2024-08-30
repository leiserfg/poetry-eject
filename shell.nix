{
  pkgs ?
    import (builtins.fetchTarball {
      url = "https://github.com/NixOS/nixpkgs/archive/63dacb46bf939521bdc93981b4cbb7ecb58427a0.tar.gz";
    }) {},
}: 

  pkgs.mkShell {
    buildInputs = [
      pkgs.python312
      (pkgs.writeShellScriptBin "poetry" ''
        exec -a $0 ${pkgs.poetry}/bin/poetry -C ${./.} "$@"
      '')
    ];
    shellHook = ''
      pre-commit install
      poetry env use ${pkgs.lib.getExe pkgs.python312}
      export VIRTUAL_ENV=$(poetry env info --path)
      export PATH=$VIRTUAL_ENV/bin/:$PATH
    '';
  }
