import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import numpy as np
import pandas as pd
import re

# ----------------------
# Reset butonuyla tüm alanları temizle
# ----------------------
def reset_all():
    txt_data.delete("1.0", tk.END)
    entry_jmin.delete(0, tk.END)
    entry_jmax.delete(0, tk.END)
    for item in tree.get_children():
        tree.delete(item)
    results_notebook.select(0)
    for widget, text in [
        (txt_E1, E1_TEMPLATE),
        (txt_E2, E2_TEMPLATE),
        (txt_E3, E3_TEMPLATE),
        (txt_C1, C1_TEMPLATE),
        (txt_C2, C2_TEMPLATE),
    ]:
        widget.config(state='normal')
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.config(state='disabled')
    global df_global
    df_global = pd.DataFrame()

# ----------------------
# Tabloyu panoya kopyala (Excel uyumlu)
# ----------------------
def copy_interpolated_to_clipboard():
    if df_global.empty:
        messagebox.showerror("Hata", "Önce veri oluşturmak için Hesapla'ya basın!")
        return
    header = f"{df_global.columns[0]}\t{df_global.columns[1]}"
    lines = [header]
    for _, row in df_global.iterrows():
        h = int(row['Height']) if row['Height'].is_integer() else row['Height']
        load_str = f"{row['Load']:.3f}".replace('.', ',')
        lines.append(f"{h}\t{load_str}")
    clip_text = "\n".join(lines)
    root.clipboard_clear()
    root.clipboard_append(clip_text)
    messagebox.showinfo("Kopyalandı", "Tablo panoya kopyalandı. Excel'e yapıştırabilirsiniz.")

# ----------------------
# Hesaplama işlevi
# ----------------------
def hesapla():
    raw = txt_data.get("1.0", tk.END).strip()
    if not raw:
        messagebox.showerror("Hata", "Height–Load verilerini gir veya yapıştır!")
        return
    lines = raw.splitlines()
    height_vals, load_vals = [], []
    for idx, line in enumerate(lines, 1):
        parts = re.split(r"[, \t]+", line.strip())
        if len(parts) != 2:
            messagebox.showerror("Hata", f"{idx}. satırda 2 değer olmalı:\n{line}")
            return
        try:
            h, l = float(parts[0]), float(parts[1])
        except:
            messagebox.showerror("Hata", f"{idx}. satır sayı formatı hatası:\n{line}")
            return
        height_vals.append(h)
        load_vals.append(l)
    try:
        jmin = float(entry_jmin.get())
        jmax = float(entry_jmax.get())
    except:
        messagebox.showerror("Hata", "JackMin/JackMax değerlerini kontrol et!")
        return
    h_min, h_max = min(height_vals), max(height_vals)
    ht_list = list(range(int(h_min), int(h_max) + 5, 5))
    ld_list = np.interp(ht_list, height_vals, load_vals)
    df = pd.DataFrame({'Height': ht_list, 'Load': [round(v,3) for v in ld_list]})
    for item in tree.get_children():
        tree.delete(item)
    tree['columns'] = df.columns.tolist()
    for c in df.columns:
        tree.heading(c, text=c)
        tree.column(c, anchor='center', width=80)
    for row in df.values.tolist():
        tree.insert('', 'end', values=row)
    global df_global
    df_global = df
    nominal = max(load_vals)
    loss_limit_jack = jmax * 0.05
    mid_h_jack = (jmax - jmin) * 0.5 + jmin

    # E1: Lowering of Jack
    txt_E1.config(state='normal')
    txt_E1.delete("1.0", tk.END)
    txt_E1.insert("1.0",
        f"{E1_TITLE}\n\n"
        f"Nominal kapasite: {nominal:.2f} kg\n\n"
        f"Prosedür:\n"
        f"1) Jack’ı tam strokta ({jmax:.1f} mm) konumlandırın ve nominal yük uygulayın.\n"
        f"2) Strokun %50’sine indirin: {mid_h_jack:.1f} mm.\n\n"
        f"Kabul Kriteri:\n"
        f"• Krikonun en açık yüksekliğinin %5’i = {loss_limit_jack:.2f} mm; bu değerden fazla kalıcı indirme kaybı olmamalı."
    )
    txt_E1.config(state='disabled')

    # E2: Loss of Height with Time
    h66_curve = (h_max - h_min) * 0.66 + h_min
    txt_E2.config(state='normal')
    txt_E2.delete("1.0", tk.END)
    txt_E2.insert("1.0",
        f"{E2_TITLE}\n\n"
        f"Nominal kapasite: {nominal:.2f} kg\n\n"
        f"Prosedür:\n"
        f"1) Yük eğrisi min/max aralığında %66 noktasına ({h66_curve:.1f} mm) kadar kaldırın; yük = nominal kapasite ({nominal:.2f} kg).\n"
        f"2) 30 dakika bekletin ve yükseklik kaybını ölçün.\n\n"
        f"Kabul Kriteri:\n"
        f"• 30 dakikada yükseklik kaybı ≤ 5 mm olmalı."
    )
    txt_E2.config(state='disabled')

    # E3: Jack Offset Loading
    txt_E3.config(state='normal')
    txt_E3.delete("1.0", tk.END)
    txt_E3.insert("1.0",
        f"{E3_TITLE}\n\n"
        f"Prosedür:\n"
        f"1) Jack’ı tam strokta ({jmax:.1f} mm) konumlandırın.\n"
        f"2) Yük eğrisindeki max yükü ({nominal:.2f} kg) uygulayın.\n\n"
        f"Kabul Kriteri:\n"
        f"• Jack normal fonksiyonunu korumalı; kayıp/çökme olmamalı."
    )
    txt_E3.config(state='disabled')

    # C1: Proof Load Test
    h33 = (h_max - h_min)/3 + h_min
    h66 = 2*(h_max - h_min)/3 + h_min
    h99 = h_max
    w33 = np.interp(h33, height_vals, load_vals) * 2
    w66 = np.interp(h66, height_vals, load_vals) * 2
    w99 = np.interp(h99, height_vals, load_vals) * 2
    txt_C1.config(state='normal')
    txt_C1.delete("1.0", tk.END)
    txt_C1.insert("1.0",
        f"{C1_TITLE}\n\n"
        f"Nominal kapasite: {nominal:.2f} kg\n"
        f"Proof Load (33%): {w33:.2f} kg at {h33:.1f} mm\n"
        f"Proof Load (66%): {w66:.2f} kg at {h66:.1f} mm\n"
        f"Proof Load (99%): {w99:.2f} kg at {h99:.1f} mm\n\n"
        f"Kabul Kriteri:\n"
        f"- Kalıcı defleksiyon ≤ 6,0 mm."
    )
    txt_C1.config(state='disabled')

    # C2: Overload Test
    overload = nominal * 2
    height_loss_limit = h66_curve * 0.05
    txt_C2.config(state='normal')
    txt_C2.delete("1.0", tk.END)
    txt_C2.insert("1.0",
        f"{C2_TITLE}\n\n"
        f"Nominal kapasite: {nominal:.2f} kg\n"
        f"Overload (%200): {overload:.2f} kg at {h66_curve:.1f} mm\n\n"
        f"Kabul Kriteri:\n"
        f"• Test yüksekliğinin %5’i = {height_loss_limit:.2f} mm; bu değerden fazla yükseklik kaybı olmamalı."
    )
    txt_C2.config(state='disabled')

# ----------------------
# GUI bileşenlerini oluştur
# ----------------------
root = tk.Tk()
root.title("Jack–Load Test Prosedürleri")

frame_top = tk.Frame(root)
frame_top.pack(fill='x', padx=10, pady=5)
tk.Label(frame_top, text="Height    Load (kopyala-yapıştır)").pack(anchor='w')
txt_data = scrolledtext.ScrolledText(frame_top, width=40, height=6)
txt_data.pack(fill='x')

frame_params = tk.Frame(root)
frame_params.pack(fill='x', padx=10)
tk.Label(frame_params, text="JackMin (mm):").grid(row=0, column=0)
entry_jmin = tk.Entry(frame_params, width=8); entry_jmin.grid(row=0, column=1)
tk.Label(frame_params, text="JackMax (mm):").grid(row=0, column=2)
entry_jmax = tk.Entry(frame_params, width=8); entry_jmax.grid(row=0, column=3)

tool_frame = tk.Frame(root)
tool_frame.pack(pady=5)
tk.Button(tool_frame, text="Hesapla", command=hesapla).pack(side='left', padx=5)
tk.Button(tool_frame, text="Temizle", command=reset_all).pack(side='left', padx=5)
tk.Button(tool_frame, text="Excel'e Kopyala", command=copy_interpolated_to_clipboard).pack(side='left', padx=5)

results_notebook = ttk.Notebook(root)
results_notebook.pack(fill='both', expand=True, padx=10, pady=5)

# Titles and templates
E1_TITLE = "E.1 Lowering of Jack"
E2_TITLE = "E.2 Loss of Height with Time"
E3_TITLE = "E.3 Jack Offset Loading"
C1_TITLE = "C.1 Proof Load Test"
C2_TITLE = "C.2 Overload Test"

E1_TEMPLATE = (
    f"{E1_TITLE}\n\nProsedür ve kabul kriterleri buraya..."
)
E2_TEMPLATE = (
    f"{E2_TITLE}\n\nProsedür ve kabul kriterleri buraya..."
)
E3_TEMPLATE = (
    f"{E3_TITLE}\n\nProsedür ve kabul kriterleri buraya..."
)
C1_TEMPLATE = (
    f"{C1_TITLE}\n\nProof load hesaplamaları sonrası buraya eklenecek"
)
C2_TEMPLATE = (
    f"{C2_TITLE}\n\nOverload hesaplamaları sonrası buraya eklenecek"
)

# Create tabs
for title, txt_var, template in [
    (E1_TITLE, 'txt_E1', E1_TEMPLATE),
    (E2_TITLE, 'txt_E2', E2_TEMPLATE),
    (E3_TITLE, 'txt_E3', E3_TEMPLATE),
    (C1_TITLE, 'txt_C1', C1_TEMPLATE),
    (C2_TITLE, 'txt_C2', C2_TEMPLATE),
]:
    tab = tk.Frame(results_notebook)
    widget = globals()[txt_var] = tk.Text(tab, wrap='word', height=12)
    widget.insert('1.0', template)
    widget.config(state='disabled')
    widget.pack(fill='both', expand=True)
    results_notebook.add(tab, text=title)

# Interpolated Data tab
data_tab = tk.Frame(results_notebook)
tk.Label(data_tab, text="5 mm aralıklarla yükseklik-eğri verisi").pack(anchor='w')
tree = ttk.Treeview(data_tab, show='headings')
tree.pack(side='left', expand=True, fill='both')
y_scroll = ttk.Scrollbar(data_tab, orient='vertical', command=tree.yview)
tree.configure(yscrollcommand=y_scroll.set)
y_scroll.pack(side='right', fill='y')
results_notebook.add(data_tab, text="Interpolated Data")

# Global DataFrame
df_global = pd.DataFrame()

root.mainloop()
