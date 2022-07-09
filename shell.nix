{ pkgs ? import <nixpkgs> {} }:

let
  openldapLibFix = pkgs.writeTextFile {
    name = "openldap-lib-fix";
    destination = "/lib/libldap_r.so";
    text = "INPUT ( libldap.so )\n";
  };
  openldap = pkgs.buildEnv {
    name = "openldap-env";
    paths = [ pkgs.openldap openldapLibFix ];
  };
in
pkgs.mkShell {
  buildInputs = [
    pkgs.bashInteractive
    pkgs.cyrus_sasl
    pkgs.libmysqlclient
    pkgs.poetry
    openldap
  ];
}
