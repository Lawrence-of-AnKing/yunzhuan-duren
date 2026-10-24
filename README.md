# 云篆度人经

把《正统道藏》本《元始无量度人上品妙经》云篆整理为可输入、可修改的开源字体。由「执笔之龙」制作。

- **907 个释文字，4616 个云篆字形**。只发布全字版：书中每处出现的云篆均单独保留。
- 直接输入简体汉字显示云篆；支持对应的部分繁体映射。
- 同一字的其他写法通过 OpenType `salt` / `aalt` 选择；`calt` 默认启用，每字至多轮换前 12 种写法。
- 支持横排、竖排。未收录的字显示缺字框。
- 字体与字形源文件使用 **SIL OFL 1.1**，代码使用 **MIT**。允许商用；再分发和修改须遵守对应许可证。

## 直接使用

安装 `dist/YunZhuanDuRen-Unmerged.ttf` 即可。在支持替代字形的排版软件中，可打开“字形／替代字”面板挑选写法。

关闭“上下文替代”可固定默认写法；网页可使用 `font-feature-settings: "calt" 0`。

## 从源文件构建

需要 Python 3.10 或更新版本。以下命令在仓库根目录运行：

```sh
python -m venv .venv
# 激活虚拟环境后：
python -m pip install -r requirements.txt
python font/build_font.py
```

macOS/Linux 激活：`source .venv/bin/activate`；Windows PowerShell 激活：`.venv\Scripts\Activate.ps1`。

输出为 `dist/YunZhuanDuRen-Unmerged.ttf`。构建只需 fontTools 和 OpenCC，无需原扫描、OCR、显卡、Potrace 或历史缓存。

源文件 `font/outlines.json` 保存定稿字体的二次贝塞尔轮廓，按原书字形 ID 索引；`font/variants.json` 保存释文、分组及默认字形，叠加 `edits/font_choices.json` 的人工选择。分组只用于组织选择与轮换次序，构建始终保留全部 4616 个字形。

同一依赖版本和源数据下，构建结果确定。构建时间默认固定，可用标准环境变量 `SOURCE_DATE_EPOCH` 指定。

## 校对与继续修改

```sh
python font/build_variants_page.py
python review_server.py
```

浏览器打开终端显示的地址，可搜索字、挑默认写法、拆分或合并写法组，修改自动保存。重新运行字体构建即可应用选择，仍保留全部字形。

仓库也保留本书的笔画级校对工具及已定稿标注。它需要使用者自行提供同尺寸的原扫描页。

详见 [校对说明](docs/校对.md) 与 [来源、许可及文件范围](docs/来源与许可.md)。

## 目录

| 路径 | 内容 |
|---|---|
| `dist/` | 可安装的全字版 TTF、OFL 及使用说明 |
| `font/outlines.json` | 4616 个定稿字形的轮廓源，坐标单位为 1000 UPM |
| `font/variants.json` | 907 个释文字到原书字形 ID 的映射与分组 |
| `glyphs/p01` 至 `p12` | 单字透明 PNG 与原书位置索引 |
| `v5/`、`v6p02/` 至 `v6p12/` | 本书各列的笔画片与释文标注，目录名沿用原工程 |
| `edits/font_choices.json` | 已审定的默认字形与分组选择 |
| `docs/` | 校对、来源和许可说明 |

## 已知限制

字形忠实保留底本的粗细变化与相对大小，没有统一重描。释文以底本实际印字为准，可能与通行经文不同。仍可能存在残笔、粘连、杂点或释文错误，欢迎附原书位置提出修正。

笔画校对与轮廓源是两个层次：修改笔画 PNG 不会暗中覆盖定稿轮廓。如何同步见校对说明。

## 致谢

感谢逍遥子的道教真文字典提供检索参考。本项目的字形来自所用底本的逐字整理，不随仓库再分发该字典或第三方资料全集。
