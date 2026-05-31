type Props = {
  columns: string[];
  rows: Record<string, unknown>[];
  emptyMessage?: string;
};

export function DataGrid({ columns, rows, emptyMessage = "No rows." }: Props) {
  if (!columns.length) {
    return <p className="hint">{emptyMessage}</p>;
  }

  return (
    <div className="table-wrap">
      <table className="data-grid">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="hint">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map((row, i) => (
              <tr key={i}>
                {columns.map((col) => (
                  <td key={col}>{formatCell(row[col])}</td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

function formatCell(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
