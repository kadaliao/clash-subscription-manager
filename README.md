# Clash 订阅管理器

用于管理 Clash Verge 代理订阅配置和快速切换节点的命令行工具。

## 特性

- **订阅管理** - 更新订阅、自动备份、添加/删除订阅
- **自动同步** - 自动更新 Clash Verge 配置并重新加载，无需手动操作
- **配置验证** - 自动验证配置格式，确保下载的是 Clash 格式
- **节点管理** - 查看节点、延迟测试、快速切换

## 快速开始

### 1. 安装依赖

```bash
# 安装 uv（如未安装）
brew install uv

# 克隆项目并安装依赖
git clone <repository-url>
cd clash-subscription-manager
uv sync
```

### 2. 配置订阅

```bash
cp config.json.sample config.json
# 编辑 config.json，填入订阅 URL
```

配置示例：
```json
{
  "clash_dir": "~/.config/clash",
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

> **重要：** 订阅 URL 需要与 Clash Verge 中添加的订阅 URL **完全一致**，这样工具才能自动同步配置

### 3. 配置 Clash API

用于自动重新加载配置和节点管理功能：

```bash
cat > .clash-api-config << 'EOF'
CLASH_API_URL=http://127.0.0.1:9090
CLASH_API_SECRET=your-secret-here
EOF
```

**如何获取 API 配置：**
1. 打开 Clash Verge 应用
2. 进入「设置」→「Clash 内核」
3. 查看「外部控制器」的地址和端口（通常是 `127.0.0.1:9090`）
4. 查看「Secret」密钥并填入上面的配置文件

> **注意：** 配置 API 后，更新订阅会自动同步到 Clash Verge 并重新加载配置

## 使用方法

### 订阅管理 (clash-sub)

```bash
./clash-sub list                           # 查看所有订阅
./clash-sub update <name>                  # 更新指定订阅（自动同步）
./clash-sub update-all                     # 更新所有订阅（自动同步）
./clash-sub add <name> <url> [desc]        # 添加订阅
./clash-sub remove <name>                  # 删除订阅
./clash-sub toggle <name>                  # 启用/禁用订阅
./clash-sub restart                        # 重启 Clash 服务
```

**工作流程：**

执行 `./clash-sub update <name>` 时会自动：
1. 下载订阅配置并验证格式
2. 备份旧配置（保留最近 5 个版本）
3. 更新 Clash Verge 的配置文件
4. 通过 API 重新加载配置

全程无需手动操作！

### 节点管理 (clash-proxy)

```bash
./clash-proxy groups                       # 查看策略组
./clash-proxy nodes                        # 查看所有节点
./clash-proxy current                      # 查看当前选择
./clash-proxy test                         # 测试节点延迟
./clash-proxy switch <group> <node>        # 切换节点
```

## 使用建议

### 设置别名

在 `~/.zshrc` 或 `~/.bashrc` 添加：

```bash
export PATH="/path/to/clash-subscription-manager:$PATH"
```

### 定时更新

```bash
# 添加 cron 任务（每天凌晨 3 点更新）
0 3 * * * /path/to/clash-subscription-manager/clash-sub update-all
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
- 检查 Clash Verge 的外部控制器是否已启用
- 查看更新日志中是否显示"✓ 已通过 API 重新加载配置"

### 未找到 Clash Verge 配置
- 确保使用的是 Clash Verge 而不是其他 Clash 客户端
- 订阅 URL 需要与 Clash Verge 中添加的订阅 URL 完全一致
- 如果手动修改过 config.json 中的 URL，需要在 Clash Verge 中也同步修改

## 许可证

MIT License
