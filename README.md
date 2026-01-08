# Clash 订阅管理器

用于管理 Clash Party (mihomo-party) 代理订阅配置和快速切换节点的命令行工具。

## 特性

- **订阅管理** - 更新订阅、自动备份、添加/删除订阅
- **自动同步** - 自动更新 Clash Party 配置并重新加载，无需手动操作
- **配置验证** - 自动验证配置格式，确保下载的是 Clash 格式
- **节点管理** - 查看节点、延迟测试、快速切换

## 安装

### 方式一：通过 pip 安装（推荐）

```bash
pip install clash-subscription-manager
```

安装完成后会自动提供两个命令：

- `clash-sub` - 订阅管理器
- `clash-proxy` - 节点查看/切换工具

### 方式二：本地开发

```bash
git clone <repository-url>
cd clash-subscription-manager
uv sync
```

开发模式下建议通过 `uv run python -m clash_sub_manager.cli --help` / `uv run python -m clash_sub_manager.proxy_cli --help` 运行，也可以直接使用 `python -m clash_sub_manager.*`。

### 方式三：通过 uvx 临时运行

无需提前安装，可使用 `uvx`（uv >= 0.4）直接执行：

```bash
uvx --from clash-subscription-manager clash-sub --help
uvx --from clash-subscription-manager clash-sub init-config
uvx --from clash-subscription-manager clash-proxy groups
```

`uvx` 会自动拉取并缓存依赖，适合一次性使用或 CI/CD 脚本。

## 快速开始

### 1. 初始化配置

```bash
clash-sub init-config
# 默认写入 ~/.config/clash-sub-manager/config.json
# 然后编辑配置文件，填入订阅与 Clash Party 路径
```

初始化时默认将 `work_dir` 指向配置文件所在目录，并会尝试自动扫描系统中常见的 Clash Party/mihomo-party 安装路径，若检测到会自动填入 `clash_party_dir`。如未找到，可手动修改配置文件。

配置示例：
```json
{
  "work_dir": "~/.config/clash-sub-manager",
  "clash_party_dir": "~/Library/Application Support/mihomo-party",
  "subscriptions": {
    "my-proxy": {
      "url": "https://your-subscription-url",
      "enabled": true,
      "description": "我的代理"
    }
  },
  "backup": {
    "enabled": true,
    "max_backups": 5
  },
  "auto_restart": true
}
```

> **重要：**
> - `work_dir`: 脚本的工作目录（默认与 `config.json` 同目录）
> - `clash_party_dir`: Clash Party 的配置目录（`clash-sub init-config` 会尝试自动检测）
> - 订阅 URL 需要与 Clash Party 中添加的订阅 URL **完全一致**
> - 脚本会自动通过 URL 匹配找到对应的 profile ID

### 2. 配置 Clash API

用于自动重新加载配置和节点管理功能，工具默认从 `~/.config/clash-sub-manager/.clash-api-config` 读取，可以通过 `--api-config` 指定其他路径。

```bash
cat > ~/.config/clash-sub-manager/.clash-api-config <<'EOF'
CLASH_API_URL=http://127.0.0.1:9090
CLASH_API_SECRET=your-secret-here
EOF
```

**如何获取 API 配置：**
1. 打开 Clash Party 应用
2. 进入「设置」→「外部控制」
3. 查看「外部控制器」的地址和端口（通常是 `127.0.0.1:9090`）
4. 查看「Secret」密钥并填入上面的配置文件

> **注意：** 配置 API 后，更新订阅会自动同步到 Clash Party 并重新加载配置

## 使用方法

所有命令都支持 `--config` 与 `--api-config` 参数来覆盖默认路径，方便在不同机器或 CI 环境中使用。

### 订阅管理 (clash-sub)

```bash
clash-sub list                           # 查看所有订阅
clash-sub update <name>                  # 更新指定订阅（自动同步）
clash-sub update-all                     # 更新所有订阅（自动同步）
clash-sub add <name> <url> [desc]        # 添加订阅
clash-sub remove <name>                  # 删除订阅
clash-sub toggle <name>                  # 启用/禁用订阅
clash-sub restart                        # 重启 Clash 服务
clash-sub init-config                    # 快速生成配置模板
```

**工作流程：**

执行 `./clash-sub update <name>` 时会自动：
1. 下载订阅配置到工作目录并验证格式
2. 备份旧配置（保留最近 5 个版本）
3. 通过 URL 自动匹配 Clash Party 中的订阅配置
4. 更新 Clash Party 的 `profiles/<profile_id>.yaml` 文件
5. 通过 API 重新加载配置

全程无需手动操作！

### 节点管理 (clash-proxy)

```bash
clash-proxy groups                       # 查看策略组
clash-proxy nodes                        # 查看所有节点
clash-proxy current                      # 查看当前选择
clash-proxy test                         # 测试节点延迟
clash-proxy switch <group> <node>        # 切换节点
```

## 使用建议

### 设置别名

如果选择本地开发模式，可在 `~/.zshrc` 或 `~/.bashrc` 添加：

```bash
export PATH="/path/to/clash-subscription-manager:$PATH"
```

### 定时更新

```bash
# 添加 cron 任务（每天凌晨 3 点更新）
0 3 * * * clash-sub update-all
```

## 使用示例

### 更新订阅
```bash
$ ./clash-sub update x-superflash
============================================================
更新订阅: x-superflash
============================================================

✓ 备份已保存: x-superflash.20251113_004117.yaml
正在下载配置...
✓ 配置已更新 (大小: 96.7 KB)
✓ 代理节点数量: 33
✓ 已更新 Clash Verge 配置文件
✓ 已通过 API 重新加载配置
```

### 查看节点状态
```bash
$ ./clash-proxy current
======================================================================
当前代理选择
======================================================================

📦 🔰 节点选择    [Selector  ] -> 极速 专线 美国 03 282ms
📦 ♻️ 自动选择    [URLTest   ] -> 极速 专线 日本 02 100ms
📦 🌏 ChatGPT    [Selector  ] -> 极速 专线 日本 01 98ms
```

## 故障排除

### 无法下载订阅
- 检查网络连接是否正常
- 确认订阅 URL 是否有效且可访问
- 确保订阅服务商支持 Clash 格式（工具会自动添加 Clash User-Agent）

### 配置格式错误
- 工具会自动验证下载的配置是否为有效的 Clash YAML 格式
- 如果提示格式错误，请联系订阅服务商获取 Clash 专用订阅链接
- 或使用订阅转换服务（如 sub-web）转换为 Clash 格式

### 更新后节点仍然超时
- 确保已配置 `.clash-api-config` 文件
- 检查 Clash Party 的外部控制器是否已启用
- 查看更新日志中是否显示"✓ 已通过 API 重新加载配置"

### 未找到 Clash Party 配置
- 确保使用的是 Clash Party 而不是其他 Clash 客户端
- 订阅 URL 需要与 Clash Party 中添加的订阅 URL 完全一致
- 可以在 Clash Party 的订阅列表中查看已添加的订阅 URL

## 许可证

MIT License
