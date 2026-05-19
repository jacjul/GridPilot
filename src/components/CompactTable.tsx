import { type ReactNode } from "react"

export type Column<T> = {
  header: string
  cell: (row: T) => ReactNode
}

type CompactTableProps<T> = {
  rows: T[]
  columns: Column<T>[]
  emptyMessage?: string
}

export function CompactTable<T>({ rows, columns, emptyMessage = "No data" }: CompactTableProps<T>) {
  if (!rows.length) {
    return <p className="text-xs text-slate-500">{emptyMessage}</p>
  }

  return (
    <div className="overflow-auto rounded border border-slate-200">
      <table className="min-w-full border-collapse text-xs">
        <thead className="bg-slate-100 text-slate-700">
          <tr>
            {columns.map((column) => (
              <th key={column.header} className="border-b border-slate-200 px-2 py-1 text-left font-semibold">
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex} className="odd:bg-white even:bg-slate-50">
              {columns.map((column) => (
                <td key={column.header} className="border-b border-slate-200 px-2 py-1 text-slate-700">
                  {column.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "-"
  }
  if (typeof value === "object") {
    return JSON.stringify(value)
  }
  return String(value)
}

type KeyValueTableProps = {
  data: Record<string, unknown> | null
  emptyMessage?: string
}

export function KeyValueTable({ data, emptyMessage = "No data" }: KeyValueTableProps) {
  if (!data) {
    return <p className="text-xs text-slate-500">{emptyMessage}</p>
  }

  const entries = Object.entries(data)

  return (
    <div className="overflow-auto rounded border border-slate-200">
      <table className="min-w-full border-collapse text-xs">
        <thead className="bg-slate-100 text-slate-700">
          <tr>
            <th className="border-b border-slate-200 px-2 py-1 text-left font-semibold">Field</th>
            <th className="border-b border-slate-200 px-2 py-1 text-left font-semibold">Value</th>
          </tr>
        </thead>
        <tbody>
          {entries.map(([key, value]) => (
            <tr key={key} className="odd:bg-white even:bg-slate-50">
              <td className="border-b border-slate-200 px-2 py-1 text-slate-700">{key}</td>
              <td className="border-b border-slate-200 px-2 py-1 text-slate-700">{formatValue(value)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
