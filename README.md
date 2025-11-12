# Clash 订阅管理器

一个简单易用的 Python 工具集，用于管理和更新 Clash 代理订阅配置，以及快速切换代理节点。

## ✨ 特性

### 订阅管理 (clash-sub)
- 📝 **配置文件管理** - 使用 JSON 配置文件保存订阅地址，不用再记忆
- 🔄 **一键更新** - 快速更新单个或所有订阅
- 💾 **自动备份** - 更新前自动备份配置，支持保留多个历史版本
- 🎨 **友好界面** - 彩色终端输出，信息清晰易读
- 🔧 **灵活管理** - 添加、删除、启用/禁用订阅
- 🚀 **自动重启** - 更新后可自动重启 Clash 服务

### 代理管理 (clash-proxy)
- 🎯 **节点选择** - 快速查看和切换代理节点
- 📊 **延迟测试** - 测试所有节点延迟，自动排序
- 🔍 **策略组管理** - 查看和管理策略组配置
- ⚡ **API 集成** - 通过 Clash API 实时控制代理

### 通用特性
- ⚡ **现代化工具** - 使用 uv 管理依赖，速度快、零配置
- 🇨🇳 **国内优化** - 预配置阿里云镜像源，下载速度快
- 🔐 **配置文件** - 支持 .clash-api-config 统一管理 API 配置

## 📦 安装

### 1. 克隆或下载项目

```bash
git clone <repository-url>
cd clash-subscription-manager
```

### 2. 安装 uv（如果还未安装）

```bash
# macOS/Linux
brew install uv

# 或者使用官方安装脚本
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. 安装依赖

使用 uv 自动创建虚拟环境并安装依赖（已配置阿里云镜像源，国内下载速度快）：

```bash
uv sync
```

### 4. 配置订阅

复制示例配置并编辑：

```bash
cp config.json.sample config.json
```

编辑 `config.json` 文件，填入你的订阅信息：

```json
{
  "clash_dir": "~/.config/clash",
  "subscriptions": {
    "x-superflash": {
      "url": "https://your-subscription-url-here",
      "enabled": true,
      "description": "X-Superflash 订阅"
    }
  },
  "backup": {
    "enabled": true,
    "max_backups": 5
  },
  "auto_restart": true
}
```

### 5. 配置 Clash API（可选，用于代理管理）

如果需要使用 `clash-proxy` 工具管理代理节点，需要配置 Clash API：

创建 `.clash-api-config` 文件（或复制示例）：

```bash
cat > .clash-api-config << 'EOF'
# Clash API 配置
# 这个文件存储你的 Clash API 访问信息

CLASH_API_URL=http://127.0.0.1:9090
CLASH_API_SECRET=your-secret-here
EOF
```

> 💡 提示：Clash API 的端口和密钥可以在 Clash Verge 的设置中找到

## 🚀 使用方法

项目提供了两个工具：
- `clash-sub` - 订阅管理工具
- `clash-proxy` - 代理节点管理工具

### 方式一：使用便捷脚本（推荐）

```bash
# 直接运行（已自动处理路径和虚拟环境）
./clash-sub list
./clash-proxy groups
```

### 方式二：使用 uv run

```bash
uv run python clash_sub_manager.py list
uv run python clash_proxy_selector.py groups
```

---

## 📚 订阅管理 (clash-sub)

### 查看所有订阅

```bash
./clash-sub list
```

显示所有已配置的订阅，包括状态、描述、文件大小和更新时间。

### 更新指定订阅

```bash
./clash-sub update x-superflash
```

更新指定名称的订阅配置。

### 更新所有订阅

```bash
./clash-sub update-all
```

更新所有启用的订阅配置。

### 添加新订阅

```bash
./clash-sub add myproxy "https://example.com/subscription" "我的代理"
```

参数说明：
- `myproxy` - 订阅名称（必填）
- 订阅 URL（必填）
- 描述信息（可选）

### 删除订阅

```bash
./clash-sub remove myproxy
```

### 启用/禁用订阅

```bash
./clash-sub toggle myproxy
```

切换订阅的启用状态。禁用的订阅不会在 `update-all` 时更新。

### 重启 Clash 服务

```bash
./clash-sub restart
```

手动重启 Clash 服务以应用新配置。

---

## 🎯 代理管理 (clash-proxy)

### 查看策略组

```bash
./clash-proxy groups
```

显示所有策略组及其当前选择的节点。

### 查看所有节点

```bash
./clash-proxy nodes
```

列出所有可用的代理节点及其延迟信息。

### 查看当前选择

```bash
./clash-proxy current
```

显示各个策略组当前选择的节点及延迟。

### 测试节点延迟

```bash
./clash-proxy test
```

测试所有节点的延迟并按速度排序显示。

### 切换节点

```bash
./clash-proxy switch PROXY "Hong Kong 01"
```

切换指定策略组到指定节点。

> 💡 提示：如果节点名包含空格，需要用引号括起来

## 📋 配置说明

### config.json - 订阅配置

```json
{
  "clash_dir": "~/.config/clash",        // Clash 配置目录
  "subscriptions": {                      // 订阅列表
    "订阅名称": {
      "url": "订阅URL",                   // 必填
      "enabled": true,                    // 是否启用
      "description": "描述信息"           // 可选描述
    }
  },
  "backup": {
    "enabled": true,                      // 是否启用自动备份
    "max_backups": 5                      // 保留的备份数量
  },
  "auto_restart": true                    // 更新后是否自动重启 Clash
}
```

### .clash-api-config - API 配置

```bash
# Clash API 配置
CLASH_API_URL=http://127.0.0.1:9090
CLASH_API_SECRET=your-secret-here
```

参数说明：
- `CLASH_API_URL`: Clash API 地址（通常是 http://127.0.0.1:9090）
- `CLASH_API_SECRET`: API 访问密钥（在 Clash 设置中可以找到）

> 💡 Python 脚本会自动读取此配置文件，命令行参数 `--api` 和 `--secret` 可以覆盖配置文件的设置

## 💡 使用建议

### 1. 设置别名（强烈推荐）

在 `~/.zshrc` 或 `~/.bashrc` 中添加：

```bash
# 获取项目的绝对路径
PROJECT_DIR="/path/to/clash-subscription-manager"

alias clash-sub="$PROJECT_DIR/clash-sub"
alias clash-proxy="$PROJECT_DIR/clash-proxy"
```

或者添加到 PATH：

```bash
export PATH="/path/to/clash-subscription-manager:$PATH"
```

然后就可以在任何目录直接使用：

```bash
clash-sub list
clash-sub update-all
clash-proxy groups
clash-proxy test
```

### 2. 定时自动更新

使用 cron 定时任务自动更新订阅：

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天凌晨 3 点更新）
0 3 * * * /path/to/clash-subscription-manager/clash-sub update-all
```

### 3. 快速切换订阅

如果你有多个订阅源，可以：

```bash
# 禁用当前订阅
clash-sub toggle x-superflash

# 添加并启用新订阅
clash-sub add backup-proxy "https://backup-url" "备用订阅"
clash-sub update backup-proxy
```

### 4. 快速切换到最快节点

```bash
# 测试所有节点并查看最快的
clash-proxy test

# 切换到最快的节点
clash-proxy switch PROXY "最快节点名称"
```

## 🔧 高级功能

### 备份管理

- 备份文件保存在 `~/.config/clash/backups/` 目录
- 文件名格式：`订阅名.时间戳.yaml`
- 自动清理超出数量限制的旧备份

### 多订阅管理

你可以在 `config.json` 中配置多个订阅：

```json
{
  "subscriptions": {
    "main": {
      "url": "https://main-subscription-url",
      "enabled": true,
      "description": "主订阅"
    },
    "backup": {
      "url": "https://backup-subscription-url",
      "enabled": false,
      "description": "备用订阅"
    }
  }
}
```

然后可以快速切换：

```bash
clash-sub toggle main      # 禁用主订阅
clash-sub toggle backup    # 启用备用订阅
clash-sub update backup    # 更新备用订阅
```

## 📝 示例输出

### 列出订阅

```
============================================================
订阅列表
============================================================

📦 x-superflash
   状态: 启用
   描述: X-Superflash 订阅
   URL: https://example.com/subscription...
   文件: 存在 (94.0 KB)
   更新: 2025-06-13 22:18:00
```

### 更新订阅

```
============================================================
更新订阅: x-superflash
============================================================

✓ 备份已保存: x-superflash.20250613_221800.yaml
正在下载配置...
✓ 配置已更新 (大小: 94.5 KB)
✓ 代理节点数量: 15

正在重启 Clash 服务...
✓ Clash 服务已重启
```

## ⚠️ 注意事项

1. **订阅 URL 安全** - 配置文件包含订阅 URL，请妥善保管
2. **网络连接** - 更新订阅需要网络连接
3. **权限问题** - 重启 Clash 服务可能需要 sudo 权限
4. **配置兼容性** - 确保下载的配置文件与你的 Clash 版本兼容

## 🐛 故障排除

### 无法下载订阅

- 检查网络连接
- 确认订阅 URL 是否有效
- 检查是否需要代理才能访问订阅 URL

### 无法重启服务

- 尝试手动重启 Clash 应用
- 检查 Clash 服务是否正在运行
- 确认服务名称是否正确

### 配置文件格式错误

- 使用 JSON 验证工具检查 config.json
- 确保所有引号和逗号正确
- URL 中如有特殊字符需要转义

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
