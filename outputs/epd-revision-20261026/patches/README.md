# 官方源码累计补丁与实际字节

官方基线是 [vbdi/epdserve](https://github.com/vbdi/epdserve/tree/9b111f710dfb4724072b603d626a1e4dad93ef1f)，固定 commit `9b111f710dfb4724072b603d626a1e4dad93ef1f`。`epdserve-9b-to-revision.patch` 合并了历史兼容、RGB/cache修正、观测接口及本批参数与metadata改动；不能将它描述成零补丁原生实现。

累计补丁只覆盖官方仓库内的 Python 文件；客户端、baseline、RGB预载和observer实现直接见本批 [scripts](../scripts)。实际代码守卫以 `configs/code-manifest.json` 的53项SHA为准。权重来源/逐文件revision及SHA见 `configs/minicpm-download-source-manifest.json`，迁移源匹配见 `configs/migrated-model-and-dependency-source-pins.json`。历史freeze中声明的cuBLAS12.1.3.1不等于本次实际加载的12.4.5.8，不能混作同一版本。

累计补丁为了可读性统一使用LF；实际运行源拷贝保留了记录时的行尾。CPU重建已经验证：干净官方版本应用补丁后，21个Python文件与实际源码的LF规范化内容逐SHA相同，AST相同；再覆盖提供的原样源码后，22个源文件（含官方原JPEG）的实际SHA逐项匹配运行清单。见 [重建证据](reconstruction-check.json)。这不新增模型正确性或GPU运行证明。

从干净仓库准备代码的步骤如下；在仓库根目录将 `BATCH` 设为本批次绝对路径，将 `EPD_SOURCE` 设为新的、可写的源码绝对路径：

```bash
git -c core.autocrlf=false clone https://github.com/vbdi/epdserve.git "$EPD_SOURCE"
git -C "$EPD_SOURCE" -c core.autocrlf=false checkout --detach 9b111f710dfb4724072b603d626a1e4dad93ef1f
git -C "$EPD_SOURCE" -c core.autocrlf=false apply --check "$BATCH/patches/epdserve-9b-to-revision.patch"
git -C "$EPD_SOURCE" -c core.autocrlf=false apply --whitespace=nowarn "$BATCH/patches/epdserve-9b-to-revision.patch"
# 原样覆盖只用于恢复记录的源码字节与行尾，不能省略SHA核验。
cp -a "$BATCH/src/epdserve/." "$EPD_SOURCE/"
python3 - "$BATCH/patches/reconstruction-check.json" "$EPD_SOURCE" <<'PY'
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[2]).resolve()
rows = json.loads(Path(sys.argv[1]).read_text())["exact_source_overlay_files"]
if len(rows) != 22:
    raise SystemExit("unexpected source inventory")
for row in rows:
    path = (root / row["path"]).resolve()
    if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
        raise SystemExit("source SHA mismatch: " + row["path"])
print("source SHA PASS: 22 files; CPU only")
PY
```

普通完整clone含原官方JPEG；若只做稀疏checkout，API导入所需 `assets/images/image2_4032_3024.jpg` 也须恢复。提供的JPEG已核对固定官方Git blob，未作替换或修改。历史首次启动缺JPEG、后续修复和全部失败记录保留。

本批执行脚本还绑定了qjh000、专属root、GPU UUID和当时预约窗口；上面的代码重建不代表任意主机已经可以运行。新GPU复跑仍须重新审查资源/窗口、环境、通信与模型机制，不能复制历史PASS marker。当前lite观察机制失败，不因补丁可重建就称其已生效；正式C使用off。
