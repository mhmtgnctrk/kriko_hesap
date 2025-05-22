import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import numpy as np
import pandas as pd


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
# Hesaplama işlevi
# ----------------------
def hesapla():
    raw = txt_data.get("1.0", tk.END).strip()
    if not raw:
        messagebox.showerror("Hata", "Height(Yükesklik)–Load(Yük) verilerini gir veya yapıştır!")
        return
    # parse input table
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
        messagebox.showerror("Hata", "Kriko Min/Kriko Max değerlerini kontrol et!")
        return

    # interpolation table (5 mm steps)
    h_min, h_max = min(height_vals), max(height_vals)
    ht_list = list(range(int(h_min), int(h_max) + 5, 5))
    ld_list = np.interp(ht_list, height_vals, load_vals)
    df = pd.DataFrame({'Height': ht_list, 'Load': [round(v,3) for v in ld_list]})
    for item in tree.get_children(): tree.delete(item)
    tree['columns'] = df.columns.tolist()
    for c in df.columns:
        tree.heading(c, text=c)
        tree.column(c, anchor='center', width=80)
    for row in df.values.tolist():
        tree.insert('', 'end', values=row)
    global df_global; df_global = df

    # nominal capacity
    nominal = max(load_vals)

    # E1: Lowering at 50% stroke (jack travel)
    mid_h_jack = (jmax - jmin) * 0.5 + jmin
    loss_limit_jack = jmax * 0.05
    txt_E1.config(state='normal')
    txt_E1.delete("1.0", tk.END)
    txt_E1.insert("1.0",
        f"{E1_TITLE}\n\n"
        f"Nominal kapasite: {nominal:.2f} kg\n\n"
        f"Prosedür:\n"
        f"1) Krikoyu tam strokta ({jmax:.1f} mm) konumlandırın ve nominal kapasiteyi yükleyin.\n"
        f"2) Yükü değiştirmeden (ölü ağırlık) krikoyu indirin.\n"
        f"3) Strok %50’ye yani {mid_h_jack:.1f} mm değerine geldiğinde durun.\n\n"
        f"Kabul Kriteri:\n"
        f"• Kriko durduktan sonra en açık yüksekliğinin %5’inden yani,\n"
        f"  {loss_limit_jack:.2f} mm'den fazla kalıcı yükseklik kaybı olmamalı."
    )
    txt_E1.config(state='disabled')

    # E2: Loss of Height with Time at 66% of input curve bounds
    h66_curve = (h_max - h_min) * 0.66 + h_min
    txt_E2.config(state='normal')
    txt_E2.delete("1.0", tk.END)
    txt_E2.insert("1.0",
        f"{E2_TITLE}\n\n"
        f"Nominal kapasite: {nominal:.2f} kg\n\n"
        f"Prosedür:\n"
        f"1) Krikoyu, yük eğrisinin min/max aralığında %66 noktasına ({h66_curve:.1f} mm) kadar kaldırın;\n"
        f"   Nominal kapasite ({nominal:.2f} kg) yükü uygulayın.\n"
        f"2) 30 dakika bekletin ve yükseklik kaybını ölçün.\n\n"
        f"Kabul Kriteri:\n"
        f"• 30 dakikasonunda yükseklik kaybı ≤ 5 mm olmalı."
    )
    txt_E2.config(state='disabled')

    # E3: Offset Loading at full stroke with max load
    txt_E3.config(state='normal')
    txt_E3.delete("1.0", tk.END)
    txt_E3.insert("1.0",
        f"{E3_TITLE}\n\n"
        f"Prosedür:\n"
        f"1) Krikoyu tam strokta ({jmax:.1f} mm) konumlandırın.\n"
        f"2) Yük eğrisindeki max yükü ({nominal:.2f} kg) eksantrik bir şekide uygulayın.\n\n"
        f"Kabul Kriteri:\n"
        f"• Kriko normal fonksiyonunu korumalı, deformasyon ya da fonksyion kaybı olmamalı."
    )
    txt_E3.config(state='disabled')

    # C1: Proof Load Test
    h33 = (h_max - h_min) * (1/3) + h_min
    h66 = (h_max - h_min) * (2/3) + h_min
    h99 = h_max
    w33 = np.interp(h33, height_vals, load_vals) * 2
    w66 = np.interp(h66, height_vals, load_vals) * 2
    w99 = np.interp(h99, height_vals, load_vals) * 2
    txt_C1.config(state='normal')
    txt_C1.delete("1.0", tk.END)
    txt_C1.insert("1.0",
        f"{C1_TITLE}\n\n"
        f"Nominal kapasite: {nominal:.2f} kg\n\n"
        f"Prosedür:\n"
        f"Krikoya aşağıdaki her aşamadan önce 1000N yük uygulayıp yükseklik ölçülür.\n"
        f"Daha sonra yük verilip 5 dakika bekletilir.\n"
        f"5 dakika sonunda yük tekrar 1000N'a çekilir ve yükseklik tekrar ölçülür.\n"
        f"İlk ölçümle, ikinci ölçüm arasındaki fark kabul kriterine göre değerlendirilir.\n"
        f"Proof Load (99%): Krikoyu {h99:.1f} mm yüksekliğe getir.\n"
        f"Proof Load (66%): Krikoyu {h66:.1f} mm yüksekliğe getir.\n"
        f"Proof Load (33%): {w33:.2f} kg at {h33:.1f} mm\n\n"
        f"Kabul Kriteri:\n"
        f"- Kalıcı yükseklik kaybı ≤ 6,0 mm."
    )
    txt_C1.config(state='disabled')

    # C2: Overload Test
    overload = nominal * 2
    height_loss_limit = h66_curve * 0.05
    txt_C2.config(state='normal')
    txt_C2.delete("1.0", tk.END)
    txt_C2.insert("1.0",
        f"{C2_TITLE}\n\n"
        f"Nominal kapasite: {nominal:.2f} kg\n\n"
        f"Prosedür: Krikoya aşağıdaki yük 1 dakika uygulanıp kaldırıldıktan sonra yüksekliği ölçülür.\n"
        f"Test yüksekliği ile yük kalktıktan sonra ölçülen yükseklik arasındaki fark kabul kriterine göre değerlendirilir.\n"
        f"Krikoya, {overload:.2f} kg yükü {h66_curve:.1f} mm yükseklikte uygula\n\n"
        f"Kabul Kriteri:\n"
        f"• Test yüksekliğinin %5’i = {height_loss_limit:.2f} mm; yükseklik kaybı\n"
        f"  bu değerden fazla olmamalı."
    )
    txt_C2.config(state='disabled')

# ----------------------
# GUI bileşenlerini oluştur
# ----------------------
root = tk.Tk()
root.title("Ford Kriko DV Testleri Yük-Yükseklik Hesaplama Aracı")

frame_top = tk.Frame(root)
frame_top.pack(fill='x', padx=10, pady=5)
tk.Label(frame_top, text="Height(Yükseklik)    Load(Yük) (kopyala-yapıştır, yada boşluk bırakark değer gir.)").pack(anchor='w')
txt_data = scrolledtext.ScrolledText(frame_top, width=40, height=6)
txt_data.pack(fill='x')

frame_params = tk.Frame(root)
frame_params.pack(fill='x', padx=10)
tk.Label(frame_params, text="Kriko Min (mm):").grid(row=0, column=0)
entry_jmin = tk.Entry(frame_params, width=8); entry_jmin.grid(row=0, column=1)
tk.Label(frame_params, text="Kriko Max (mm):").grid(row=0, column=2)
entry_jmax = tk.Entry(frame_params, width=8); entry_jmax.grid(row=0, column=3)

tool_frame = tk.Frame(root)
tool_frame.pack(pady=5)
tk.Button(tool_frame, text="Hesapla", command=hesapla).pack(side='left', padx=5)
tk.Button(tool_frame, text="Temizle", command=reset_all).pack(side='left', padx=5)

results_notebook = ttk.Notebook(root)
results_notebook.pack(fill='both', expand=True, padx=10, pady=5)

# Titles and templates
E1_TITLE = "E.1 Lowering of Jack"
E2_TITLE = "E.2 Loss of Height with Time"
E3_TITLE = "E.3 Jack Offset Loading"
C1_TITLE = "C.1 Proof Load Test"
C2_TITLE = "C.2 Overload Test"

E1_TEMPLATE = (
    f"{E1_TITLE}\n\nHesaplamalar için yük-yükseklik eğrisi, kriko min ve kriko max bilgileri bekleniyor..."
)
E2_TEMPLATE = (
    f"{E2_TITLE}\n\nHesaplamalar için yük-yükseklik eğrisi, kriko min ve kriko max bilgileri bekleniyor..."
)
E3_TEMPLATE = (
    f"{E3_TITLE}\n\nHesaplamalar için yük-yükseklik eğrisi, kriko min ve kriko max bilgileri bekleniyor..."
)
C1_TEMPLATE = (
    f"{C1_TITLE}\n\nHesaplamalar için yük-yükseklik eğrisi, kriko min ve kriko max bilgileri bekleniyor..."
)
C2_TEMPLATE = (
    f"{C2_TITLE}\n\nHesaplamalar için yük-yükseklik eğrisi, kriko min ve kriko max bilgileri bekleniyor..."
)

# Create tabs
for title, txt_var in [(E1_TITLE, 'txt_E1'), (E2_TITLE, 'txt_E2'),
                       (E3_TITLE, 'txt_E3'), (C1_TITLE, 'txt_C1'), (C2_TITLE, 'txt_C2')]:
    tab = tk.Frame(results_notebook)
    widget = globals()[txt_var] = tk.Text(tab, wrap='word', height=12)
    widget.insert('1.0', globals()[txt_var.replace('txt_', '').upper() + '_TEMPLATE'])
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
results_notebook.add(data_tab, text="Interpole Edilmiş Yük Eğrisi")

# Global DataFrame
_df = pd.DataFrame()
df_global = _df

root.mainloop()
