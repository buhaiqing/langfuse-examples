# Frontend Development Standards

> **Purpose**: React development standards for observability dashboard  
> **Last Updated**: 2026-04-08

---

## Technology Stack

- **Framework**: React 18.3+ with TypeScript 5.0+
- **UI Library**: Ant Design 5.x + Ant Design Pro 6.x
- **Build Tool**: Vite 5.x
- **State Management**: Zustand 4.x (client) + React Query 5.x (server)
- **Routing**: React Router 6.x
- **HTTP Client**: Axios 1.x
- **Charts**: @ant-design/charts
- **Styling**: Less + CSS Modules

## Component Pattern

```typescript
import React, { useMemo } from 'react';
import { Card, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { Trace } from '@/types/trace';

interface TraceListProps {
  sessionId?: string;
  onSelect?: (trace: Trace) => void;
}

export const TraceList: React.FC<TraceListProps> = ({ sessionId, onSelect }) => {
  const columns: ColumnsType<Trace> = useMemo(() => [
    {
      title: 'Trace ID',
      dataIndex: 'id',
      key: 'id',
      width: 200
    },
    {
      title: 'Tool Name',
      dataIndex: 'toolName',
      key: 'toolName'
    }
  ], []);

  return (
    <Card title="Recent Traces">
      <Table columns={columns} dataSource={[]} rowKey="id" />
    </Card>
  );
};
```

## Rules

- ✅ ALWAYS use functional components with hooks
- ✅ ALWAYS define TypeScript interfaces for props
- ✅ ALWAYS use CSS Modules for styling
- ❌ NEVER use class components
- ❌ NEVER use inline styles
- ❌ NEVER use `any` type

---

**See Full Documentation**: Component patterns, state management, API integration, testing, and accessibility standards.
