### Ford Kriko DV Testleri Yük-Yükseklik Hesaplama Aracı
# Bu program, Ford Kriko DV testleri için yükseklik ve yük hesaplamalarını yapar.
# Kullanıcıdan yükseklik ve yük verilerini alır, interpolasyon yapar ve sonuçları gösterir.
### Kullanıcı arayüzü Tkinter ile oluşturulmuştur.
### Kullanım:
# 1. Yükseklik ve yük verilerini girin veya yapıştırın.
# 2. Kriko Min ve Kriko Max değerlerini girin.
# 3. "Hesapla" butonuna basın.
# 4. Sonuçları inceleyin ve "Excel'e Kopyala" butonuyla kopyalayın.
### version v0.1.0
# ----------------------
### yazar: mehmet gençtürk
# tarih: 2025-05-22

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import io
import win32clipboard
from PIL import Image
import numpy as np
import pandas as pd
import re

fig = None     # matplotlib Figure nesnesini tutacak

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
        h = int(row['Height (mm)']) if row['Height (mm)'].is_integer() else row['Height (mm)']
        load_str = f"{row['Load (kg)']:.3f}".replace('.', ',')
        lines.append(f"{h}\t{load_str}")
    clip_text = "\n".join(lines)
    root.clipboard_clear()
    root.clipboard_append(clip_text)
    messagebox.showinfo("Kopyalandı", "Tablo panoya kopyalandı. Excel'e yapıştırabilirsiniz.")


# ----------------------
# Excel'e veri kaydetme işlevi
# ----------------------
def export_to_excel():
    if df_global.empty:
        messagebox.showerror("Hata", "Önce Hesapla butonuna basın!")
        return

    path = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Excel Dosyası", "*.xlsx")],
        title="Excel dosyası olarak kaydet"
    )
    if not path:
        return

    # ExcelWriter'ı xlsxwriter ile başlat
    with pd.ExcelWriter(path, engine='xlsxwriter') as writer:
        # Metin sekmeleri
        for title, widget in [
            (E1_TITLE, txt_E1),
            (E2_TITLE, txt_E2),
            (E3_TITLE, txt_E3),
            (C1_TITLE, txt_C1),
            (C2_TITLE, txt_C2),
        ]:
            lines = widget.get("1.0", tk.END).strip().splitlines()
            pd.DataFrame({title: lines}) \
              .to_excel(writer, sheet_name=title[:31], index=False, header=False)

        # İnterpole edilmiş veriler
        df_global.to_excel(writer,
            sheet_name="Interpolated Data", index=False
        )

        # Chart ekleme
        workbook  = writer.book
        worksheet = writer.sheets["Interpolated Data"]

        # Yeni bir line chart oluştur
        chart = workbook.add_chart({'type': 'line'})

        # Veri aralığı
        n = len(df_global)
        # categories: ilk sütun (Height), values: ikinci sütun (Load)
        chart.add_series({
            'name':       'Load vs Height',
            'categories': ['Interpolated Data', 1, 0, n, 0],
            'values':     ['Interpolated Data', 1, 1, n, 1],
            'line':       {'width': 2},
        })

        # Chart başlıkları
        chart.set_x_axis({'name': 'Height (mm)'})
        chart.set_y_axis({'name': 'Load (kg)'})
        chart.set_title({'name': 'Interpolated Load–Height Curve'})

        # C2 hücresine chart'ı yerleştir
        worksheet.insert_chart('C2', chart, {'x_scale': 1.5, 'y_scale': 1.5})

    messagebox.showinfo("Kaydedildi", f"Excel dosyası oluşturuldu:\n{path}")

# ----------------------
# Hesaplama işlevi
# ----------------------
def hesapla():
    global fig, canvas
    raw = txt_data.get("1.0", tk.END).strip()
    if not raw:
        messagebox.showerror("Hata", "Height(Yükesklik - mm) – Load(Yük - kg) verilerini gir veya yapıştır!")
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
        messagebox.showerror("Hata", "Kriko Min/Kriko Max değerlerini kontrol et!")
        return
    try:
        step = float(entry_step.get())
        if step <= 0:
            raise ValueError
    except:
        messagebox.showerror("Hata", "Adım (mm) pozitif sayı olmalı!")
        return
    h_min, h_max = min(height_vals), max(height_vals)
    ht_list = np.arange(h_min, h_max + step/2, step).tolist()
    ld_list = np.interp(ht_list, height_vals, load_vals)
    df = pd.DataFrame({'Height (mm)': ht_list, 'Load (kg)': [round(v,3) for v in ld_list]})
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
    lbl_data.config(text=f"{step:g} mm aralıklarla yük-eğri verisi")
    nominal = max(load_vals)
    loss_limit_jack = jmax * 0.05
    mid_h_jack = (jmax - jmin) * 0.5 + jmin

    # E1: Lowering of Jack
    txt_E1.config(state='normal')
    txt_E1.delete("1.0", tk.END)
    txt_E1.insert("1.0",
        f"{E1_TITLE}\n\n"
        f"Prosedür:\n"
        f"1) Krikoyu tam strokta ({jmax:.1f} mm) konumlandırın ve nominal kapasite ({nominal:.2f} kg) yükünü uygulayın.\n"
        f"2) Yükü değiştirmeden (ölü ağırlık) krikoyu indirin.\n"
        f"3) Strok %50’ye ({mid_h_jack:.1f}) mm değerine geldiğinde durun.\n\n"
        f"Kabul Kriteri:\n"
        f"• Kriko durduktan sonra en açık yüksekliğinin %5’inden yani,\n"
        f"  {loss_limit_jack:.2f} mm'den fazla kalıcı yükseklik kaybı olmamalı."
    )
    txt_E1.config(state='disabled')

    # E2: Loss of Height with Time
    h66_curve = (h_max - h_min) * 0.66 + h_min
    txt_E2.config(state='normal')
    txt_E2.delete("1.0", tk.END)
    txt_E2.insert("1.0",
        f"{E2_TITLE}\n\n"
        f"Prosedür:\n"
        f"1) Krikoyu, yük eğrisinin min/max aralığında %66 noktasına ({h66_curve:.1f} mm) kadar kaldırın;\n"
        f"2) Nominal kapasite ({nominal:.2f} kg) yükünü uygulayın.\n"
        f"3) 30 dakika bekletin ve yükseklik kaybını ölçün.\n\n"
        f"Kabul Kriteri:\n"
        f"• 30 dakikasonunda yükseklik kaybı ≤ 5 mm olmalı."
    )
    txt_E2.config(state='disabled')

    # E3: Jack Offset Loading
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
        f"Prosedür:\n"
        f"Krikoya aşağıdaki her aşamadan önce 1000N yük uygulayıp yükseklik ölçülür.\n"
        f"Daha sonra yük verilip 5 dakika bekletilir.\n"
        f"5 dakika sonunda yük tekrar 1000N'a çekilir ve yükseklik tekrar ölçülür.\n"
        f"İlk ölçümle, ikinci ölçüm arasındaki fark kabul kriterine göre değerlendirilir.\n\n"
        f"1) Proof Load (%100): Krikoyu {h_max:.1f} mm yüksekliğe getirin ve {w99:.1f} kg yükü 5 dakika uygulayın.\n"
        f"2) Proof Load (%66): Krikoyu {h66:.1f} mm yüksekliğe getirin ve {w66:.1f} kg yükü 5 dakika uygulayın.\n"
        f"3) Proof Load (%33): Krikoyu {h33:.1f} mm yüksekliğe getirin ve {w33:.1f} kg yükü 5 dakika uygulayın.\n\n"
        f"Kabul Kriteri:\n"
        f"- Kalıcı yükseklik kaybı ≤ 6,0 mm."
    )
    txt_C1.config(state='disabled')

    # C2: Overload Test
    overload = nominal * 2
    overload_h66 = 2* (jmax - jmin) / 3 + jmin
    height_loss_limit = overload_h66 * 0.05
    txt_C2.config(state='normal')
    txt_C2.delete("1.0", tk.END)
    txt_C2.insert("1.0",
        f"{C2_TITLE}\n\n"
        f"Prosedür: Krikoya aşağıdaki yük 1 dakika uygulanıp kaldırıldıktan sonra yüksekliği ölçülür.\n"
        f"Test yüksekliği ile yük kalktıktan sonra ölçülen yükseklik arasındaki fark kabul kriterine göre değerlendirilir.\n\n"
        f"1) Krikoya, {overload:.2f} kg yükü {overload_h66:.1f} mm yükseklikte uygulayın.\n"
        f"2) 1 dakika sonra yükü kaldırıp yüksekliği ölçün ve test yüksekliği ile farkına bakın.\n\n"
        f"Kabul Kriteri:\n"
        f"• Yükseklik kaybı test yüksekliğinin %5’inden ({height_loss_limit:.2f} mm) fazla olmamalı."
    )
    txt_C2.config(state='disabled')
    
    # --- Grafik çizimi başlıyor ---
    try:
        canvas.get_tk_widget().destroy()
    except NameError:
        pass

    fig = Figure(figsize=(4,3), dpi=100)
    ax  = fig.add_subplot(111)
    ax.plot(height_vals, load_vals, marker='o', linestyle='-')
    ax.set_xlabel("Height (mm)")
    ax.set_ylabel("Load (kg)")
    ax.grid(True)

    # burayı ekle:
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=graph_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill='both', expand=True)
    # --- Grafik çizimi bitti ---

# ----------------------
# Clipboard'a grafik kopyalama işlevi
# Bu işlev, matplotlib Figure nesnesini BMP formatında panoya kopyalar.
# Windows clipboard'ı kullanır.
# Not: win32clipboard modülü Windows'a özgüdür.
# ----------------------
def copy_graph_to_clipboard():
    if fig is None:
        messagebox.showerror("Hata", "Önce Hesapla butonuna basın!")
        return

    # Figürü önce PNG olarak bellekten üret
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)

    # PIL ile PNG’yi açıp BMP’ye çevir
    img = Image.open(buf).convert('RGB')
    bmp_buf = io.BytesIO()
    img.save(bmp_buf, format='BMP')
    bmp_data = bmp_buf.getvalue()[14:]   # BITMAPFILEHEADER’ı at, geriye DIB kalsın
    buf.close()
    bmp_buf.close()

    # Windows panosuna DIB formatında koy (bu en çok kabul gören format)
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, bmp_data)
    win32clipboard.CloseClipboard()

    messagebox.showinfo("Kopyalandı", "Grafik panoya kopyalandı!")

# ----------------------
# GUI bileşenlerini oluştur
# ----------------------
root = tk.Tk()
root.title("Ford Kriko DV Testleri Yük-Yükseklik Hesaplama Aracı")

frame_top = tk.Frame(root)
frame_top.pack(fill='x', padx=10, pady=5)
tk.Label(frame_top, text="Height(Yükseklik-mm)    Load(Yük-kg) (kopyala-yapıştır, yada boşluk bırakark değer gir.)").pack(anchor='w')
txt_data = scrolledtext.ScrolledText(frame_top, width=40, height=6)
txt_data.pack(fill='x')

# Tablo ve kaydırıcılar için çerçeve
table_frame = tk.Frame(root)
table_frame.pack(padx=10, pady=5, expand=True, fill='both')

# Şimdi sağa, grafiği koyacağımız frame:
graph_frame = tk.Frame(table_frame)
graph_frame.pack(side='right', fill='both', expand=True)

frame_params = tk.Frame(root)
frame_params.pack(fill='x', padx=10)
tk.Label(frame_params, text="Kriko Min (mm):").grid(row=0, column=0)
entry_jmin = tk.Entry(frame_params, width=8); entry_jmin.grid(row=0, column=1)
tk.Label(frame_params, text="Kriko Max (mm):").grid(row=0, column=2)
entry_jmax = tk.Entry(frame_params, width=8); entry_jmax.grid(row=0, column=3)
tk.Label(frame_params, text="Adım (mm):").grid(row=0, column=4)
entry_step = tk.Entry(frame_params, width=5)
entry_step.grid(row=0, column=5)
entry_step.insert(0, "5")  # varsayılan 5 mm

tool_frame = tk.Frame(root)
tool_frame.pack(pady=5)
tk.Button(tool_frame, text="Hesapla", command=hesapla).pack(side='left', padx=5)
tk.Button(tool_frame, text="Temizle", command=reset_all).pack(side='left', padx=5)
tk.Button(tool_frame, text="Excel'e Kopyala", command=copy_interpolated_to_clipboard).pack(side='left', padx=5)
tk.Button(tool_frame, text="Excel’e Çıktı Al", command=export_to_excel).pack(side='left', padx=5)
tk.Button(tool_frame, text="Grafiği Kopyala",  command=copy_graph_to_clipboard).pack(side='left', padx=5)

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
lbl_data = tk.Label(data_tab, text="")
lbl_data.pack(anchor='w')

tree = ttk.Treeview(data_tab, show='headings')
tree.pack(side='left', expand=True, fill='both')
y_scroll = ttk.Scrollbar(data_tab, orient='vertical', command=tree.yview)
tree.configure(yscrollcommand=y_scroll.set)
y_scroll.pack(side='right', fill='y')
results_notebook.add(data_tab, text=f"İnterpole Edilmiş Yük Eğrisi")

# Global DataFrame
df_global = pd.DataFrame()

root.mainloop()
