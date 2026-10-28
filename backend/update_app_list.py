path = 'frontend/src/pages/ApplicationsList.tsx'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

c_norm = c.replace('\r\n', '\n')

# 1. Add Download to imports
old_import = 'import { PlusCircle, Search, Filter, ArrowRight, RefreshCw, FileText } from "lucide-react";'
new_import = 'import { PlusCircle, Search, Filter, ArrowRight, RefreshCw, FileText, Download } from "lucide-react";'
assert old_import in c_norm, 'old_import not found'
c_norm = c_norm.replace(old_import, new_import, 1)

# 2. Add exporting state and handler
old_state = '  const [loading, setLoading] = useState(true);'
new_state = '''  const [loading, setLoading] = useState(true);
  const [exportingCsv, setExportingCsv] = useState(false);

  const handleExportQueueCsv = async () => {
    setExportingCsv(true);
    try {
      const { blob, filename } = await api.exportApplicationsQueueCsv({
        status: statusFilter || undefined,
        category: categoryFilter || undefined,
        search: searchTerm || undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || `regulens_applications_${new Date().toISOString().split("T")[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(err.message || "Failed to export applications CSV");
    } finally {
      setExportingCsv(false);
    }
  };'''
assert old_state in c_norm, 'old_state not found'
c_norm = c_norm.replace(old_state, new_state, 1)

# 3. Add Export CSV button next to Submit Application or Refresh
old_header_right = '''        {user?.role === "INSTITUTION_USER" && (
          <Link
            to="/applications/new"
            className="inline-flex items-center gap-2 px-4 py-2 bg-[#0B2545] hover:bg-[#123B63] text-white rounded-lg text-xs font-bold transition-colors shadow-sm self-start sm:self-auto"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Submit Application</span>
          </Link>
        )}
      </div>'''

new_header_right = '''        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          <button
            onClick={handleExportQueueCsv}
            disabled={exportingCsv || loading}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-white border border-[#DCE4ED] hover:bg-slate-50 text-[#0B2545] rounded-lg text-xs font-bold transition-colors shadow-xs cursor-pointer disabled:opacity-50"
            title="Export filtered application queue to CSV"
          >
            <Download className={`w-3.5 h-3.5 text-[#1677C8] ${exportingCsv ? "animate-bounce" : ""}`} />
            <span>{exportingCsv ? "Exporting CSV..." : "Export CSV"}</span>
          </button>

          {user?.role === "INSTITUTION_USER" && (
            <Link
              to="/applications/new"
              className="inline-flex items-center gap-2 px-4 py-2 bg-[#0B2545] hover:bg-[#123B63] text-white rounded-lg text-xs font-bold transition-colors shadow-sm"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Submit Application</span>
            </Link>
          )}
        </div>
      </div>'''
assert old_header_right in c_norm, 'old_header_right not found'
c_norm = c_norm.replace(old_header_right, new_header_right, 1)

with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(c_norm.replace('\n', '\r\n'))

print('ApplicationsList.tsx updated successfully!')

