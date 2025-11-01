# Minimax 语音合成中转服务 API 文档

## 概述

这是一个基于 Flask 的语音合成中转服务，用于将客户端请求转发给 Minimax API 并返回音频流。该服务支持多种 voice 参数格式，并提供了完整的错误处理机制。

代码主要是AI写的，所以里面有详细的注释，我没有删掉，就算不懂代码也可以看懂。本身是为omate设计的，但是酒馆也可以用，如果你想自己部署，可以下载源代码然后按照下面的教程操作。有任何问题可以提issue！

## 服务信息

- **服务地址**: `http://your-server:6000`
- **主要端点**: `/audio/speech`
- **请求方法**: `POST`
- **返回格式**: 音频流 (audio/mpeg) 或 JSON 错误信息

## API 接口

### POST /audio/speech

将文本转换为语音并返回音频流。

#### 请求头 (Headers)

| 参数名 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| Authorization | string | 是 | Minimax API 的认证令牌 |
| Content-Type | string | 是 | 必须为 `application/json` |

#### 请求体 (JSON Body)

| 参数名 | 类型 | 必需 | 说明 | 示例 |
|--------|------|------|------|------|
| model | string | 是 | 语音模型名称 | `"speech-2.5-hd-preview"` |
| voice | string | 是 | 声音ID，支持多种格式 | `"minimax001"` 或 `"voice=minimax001"` |
| input | string | 是 | 要转换的文本内容 | `"你好，世界！"` |

#### URL 查询参数 (可选)

| 参数名 | 类型 | 范围 | 说明 | 示例 |
|--------|------|------|------|------|
| speed | float | [0.5, 2.0] | 语速调节 | `?speed=1.2` |
| vol | float | (0, 10.0] | 音量调节 | `?vol=8.5` |
| pitch | int | [-12, 12] | 语调调节 | `?pitch=2` |

#### Voice 参数格式支持

该服务支持以下三种 voice 参数格式：

1. **直接格式** (推荐，兼容现有软件如酒馆):
   ```json
   {
     "voice": "minimax001"
   }
   ```

2. **半角等号格式**:
   ```json
   {
     "voice": "voice=minimax001"
   }
   ```

3. **全角等号格式** (兼容用户输入错误):
   ```json
   {
     "voice": "voice＝minimax001"
   }
   ```

#### 请求示例

```bash
curl -X POST "http://localhost:6000/audio/speech?speed=1.2&vol=8.0" \
  -H "Authorization: Bearer your-minimax-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "speech-2.5-hd-preview",
    "voice": "minimax001",
    "input": "你好，这是一个测试文本。"
  }'
```

#### 成功响应

- **状态码**: 200
- **Content-Type**: `audio/mpeg`
- **响应体**: 音频流数据

#### 错误响应

##### 1. 认证失败 (401)
```json
{
  "error": "Authorization header is missing"
}
```

##### 2. 参数缺失 (400)
```json
{
  "error": "缺少必需字段（model、voice、input）"
}
```

##### 3. Minimax API 调用失败 (500)
```json
{
  "error": "调用 Minimax 接口失败",
  "status_code": 500,
  "message": "具体的错误信息"
}
```

##### 4. Minimax 任务失败 (500)
```json
{
  "error": "Minimax 返回的具体错误信息",
  "status_code": 1004,
  "status_msg": "Minimax 返回的具体错误信息"
}
```

##### 5. 音频数据缺失 (500)
```json
{
  "error": "返回中未找到音频字段"
}
```

## 特性说明

### 1. 向后兼容性
- 完全兼容现有软件（如酒馆）的直接 voice_id 格式
- 不会影响现有系统的正常运行

### 2. 输入容错
- 自动处理全角等号输入错误
- 支持多种 voice 参数格式
- 参数范围验证和警告

### 3. 隐私保护
- 日志中自动截断长文本（超过10字符显示前10字符+...）
- 避免敏感信息泄露

### 4. 错误处理
- 完整的 Minimax API 错误信息传递
- 详细的调试日志
- 友好的错误响应格式

## 部署说明

### 环境要求
- Python 3.6+
- Flask
- requests

### 安装依赖
```bash
pip install flask requests
```

### 运行服务
```bash
python app.py
```

服务将在 `http://0.0.0.0:6000` 启动。

### 生产环境部署
建议使用 Gunicorn 等 WSGI 服务器：

```bash
gunicorn -w 4 -b 0.0.0.0:6000 app:app
```

## 日志说明

服务会输出以下类型的日志：

1. **请求日志**: 显示发送给 Minimax 的请求内容（文本已截断）
2. **成功日志**: `"Minimax API 响应成功。"`
3. **错误日志**: 详细的错误信息和状态码
4. **参数解析日志**: voice 参数解析过程（仅在解析时显示）

## 注意事项

1. **认证令牌**: 确保 Authorization header 包含有效的 Minimax API 令牌
2. **参数范围**: 虽然服务会传递超出范围的参数给 Minimax，但建议使用推荐范围
3. **文本长度**: 建议控制输入文本长度，避免过长的请求
4. **错误处理**: 客户端应正确处理各种错误响应

## 更新日志

- **v2.0**: 添加全角等号兼容性支持
- **v1.0**: 基础语音合成中转功能


