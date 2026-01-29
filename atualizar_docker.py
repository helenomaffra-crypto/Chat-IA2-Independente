#!/usr/bin/env python3
"""
Mini app: atualiza e sobe o Docker com um clique (Run como app.py).

Uso:
  python atualizar_docker.py           → build + up -d (igual dar Play)
  python atualizar_docker.py --force   → build --no-cache + up -d
  python atualizar_docker.py --down    → docker compose down
"""
import subprocess
import sys
import os

def run(cmd, desc):
    print(f"\n{'='*50}\n🔧 {desc}\n{'='*50}")
    p = subprocess.run(cmd, shell=True)
    if p.returncode != 0:
        print(f"\n❌ Erro ao executar: {desc}")
        return False
    return True

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f"📁 {os.getcwd()}\n")

    if "--down" in sys.argv:
        run("docker compose down", "Parando containers (docker compose down)")
        print("\n✅ Containers parados.\n")
        return

    ok_build = (
        run("docker compose build --no-cache", "Build forçado (--no-cache)")
        if "--force" in sys.argv
        else run("docker compose build", "Build das imagens")
    )
    if not ok_build:
        sys.exit(1)
    if not run("docker compose up -d", "Subindo containers (docker compose up -d)"):
        sys.exit(1)
    run("docker compose ps", "Status")
    print("\n✅ Pronto. Acesse a aplicação (ex.: http://localhost ou porta 5001).\n")

if __name__ == "__main__":
    main()
