"""Writes final-fix-readme-blocks.zsh: every bash block of README section "Goat step 1", verbatim and in
order, with marker, timing and log-saving lines of the harness between blocks."""
import pathlib, re, sys
W = sys.argv[1]
readme = pathlib.Path("README.md").read_text()
sec = readme[readme.index("## Goat step 1: pod 1 to host"):readme.index("## Optional: Elasticsearch")]
blocks = re.findall(r"```bash\n(.*?)```", sec, re.S)
assert len(blocks) == 19, len(blocks)
names = ["helper", "1", "2", "3", "4", "5", "5.1", "5.2", "5.3", "5.4", "5.5", "6", "7", "8", "9", "9.1", "10a", "10b", "10c"]
save = lambda f, svc="": f'dg logs --no-color --timestamps {svc}> {W}/{f}'.replace("  ", " ")
before = {
    "helper": [f"cd {pathlib.Path.cwd()}", f". {W}/docker-env.sh", 'echo "=== start $(date -u +%FT%TZ)"'],
    "5": [save("final-fix-logs-1-4.txt")],
    "5.5": [save("final-fix-logs-5.txt")],
    "8": [save("final-fix-logs-6-7.txt")],
    "10a": ['echo "=== build start $(date -u +%FT%TZ) $(date +%s)"'],
    "10b": ['echo "=== build end $(date -u +%FT%TZ) $(date +%s)"'],
}
out = []
for name, block in zip(names, blocks):
    out += before.get(name, [])
    out.append(f'echo "=== block {name} $(date -u +%T)"')
    lines = block.rstrip("\n").split("\n")
    if name == "10c":
        assert lines[-1] == "dg up -d zenohd-fabric"
        lines = lines[:-1] + [save("final-fix-fabric-trace-10.txt", "zenohd-fabric ")] + lines[-1:]
    out += lines
out += [save("final-fix-logs-8-10.txt"), 'echo "=== end $(date -u +%FT%TZ)"', "dg down"]
pathlib.Path(W, "final-fix-readme-blocks.zsh").write_text("\n".join(out) + "\n")
