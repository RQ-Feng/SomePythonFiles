from pathlib import Path
import subprocess

Cache = Path(__file__).parent / "Cache"
config= Cache /  "temp.config"

if __name__ == "__main__":
    subprocess.run(
    ["D:\MCLDownload\MinecraftBENeteasePath\Default PVP Client 1.21.90\Minecraft.Windows.exe", f'config={config}'],
)