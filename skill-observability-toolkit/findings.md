# Findings: Skill Observability Toolkit

## 1. 核心差距分析

### 1.1 现有 Skill 接入路径（问题）
```
传统 Agent Skill 接入路径：
1. 开发者手动调用 `stop init` 生成新项目 ❌ 不是"无缝"
2. 手动修改代码添加 @trace_skill_execution 装饰器
3. 手动创建 skill.yaml
```

### 1.2 理想路径（目标）
```
理想路径：
1. 开发者运行: stop observe --path ./existing-skill ✅ "无缝"
2. 工具自动扫描代码，识别入口函数
3. 自动生成 skill.yaml（基于代码分析）
4. 自动注入追踪装饰器
5. 自动完成端到端追踪 ✅
```

---

## 2. 高优先级功能设计

### 2.1 stop observe 命令

#### 功能规格
```
stop observe <path> [options]

Options:
  --entry-point TEXT    指定入口函数 (默认: 自动检测)
  --output-dir DIR       输出目录 (默认: 当前目录)
  --dry-run              仅分析，不修改文件
  --force                覆盖已有文件
  --langfuse             启用 Langfuse 追踪
  --verbose              详细输出
```

#### 工作流程
1. 扫描目标目录 Python 文件
2. 使用 AST 分析识别：
   - 函数定义 (def/async def)
   - 类型注解
   - Docstrings
   - 可能的输入输出
3. 生成 skill.yaml
4. 注入追踪装饰器
5. 输出修改文件

#### 技术方案
- 使用 `ast` 模块分析代码结构
- 使用 `redbaron` 或 `libCST` 进行代码修改
- 保持原有代码格式和注释

### 2.2 自动 skill.yaml 生成

#### 输入分析
- 函数签名 (name, parameters, types)
- Docstrings (description, examples)
- 返回值类型注解
- 可能的配置文件读取

#### 输出模板
```yaml
sop: "1.0.0"
name: auto-detected-skill
version: "0.1.0"
description: "从 {filename}:{func_name} 自动生成"
inputs:
  - name: {param_name}
    type: {type}
    required: true/false
    description: "{docstring 或 自动推断}"
outputs:
  - name: result
    type: {return_type}
    description: "{docstring}"
observability:
  level: "L2"
  langfuse_integration: true
```

---

## 3. 清理计划

### 3.1 需清理的代码
- `cli/report.py:90` - HTML 格式未实现警告
- `cli/compare.py` - 功能不完整

### 3.2 需删除的文档/代码
- 无冲突代码发现
- 暂无需要删除的内容

---

## 4. OpenSkills 兼容性分析

### 4.1 OpenSkills 格式简介
- 业界标准 skill 元数据格式
- 包含: name, version, description, inputs, outputs, capabilities

### 4.2 兼容性实现
- 导入: OpenSkills YAML → skill.yaml
- 导出: skill.yaml → OpenSkills YAML
- 工作量: ~5 人日

---

## 最后更新
- 2026-04-24
