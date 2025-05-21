import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import numpy as np
import pandas as pd
import re

def hesapla():
    raw = txt_data.get('1.0', tk.END).strip()
    if not raw:
        messagebox.showerror("Hata", "Lütfen Height–Load verilerini gir veya yapıştır!")
        return
    # Satır satır parse et
    lines = raw.splitlines()
    height, load = [], []
    for idx, line in enumerate(lines, 1):
        parts = re.split(r'[,\t ]+', line.strip())
        if len(parts) != 2:
            messagebox.showerror("Hata",
                f"{idx}. satırda 2 değer olmalı!\nSatır: {line}")
            return
        try:
            h = float(parts[0]); l = float(parts[1])
        except:
            messagebox.showerror("Hata",
                f"{idx}. satırda sayı formatı hatası!\nSatır: {line}")
            return
        height.append(h); load.append(l)
    # JackMin, JackMax
    try:
        jmin = float(entry_jmin.get())
        jmax = float(entry_jmax.get())
    except:
        messagebox.showerror("Hata",
            "JackMin ve JackMax değerlerini kontrol et!")
        return

    # Piecewise linear interpolation
    ht_list = list(range(int(min(height)), int(max(height))+5, 5))
    ld_list = np.interp(ht_list, height, load)  # lineer interp
    df = pd.DataFrame({
        'Height': ht_list,
        'Load':   [round(v,3) for v in ld_list]
    })

    # Treeview güncelle
    tree["columns"] = list(df.columns)
    for c in df.columns:
        tree.heading(c, text=c)
        tree.column(c, width=80, anchor='center')
    tree.delete(*tree.get_children())
    for row in df.values.tolist():
        tree.insert('', 'end', values=row)

    # Ara %33, %66 ve çökme hesapları (lineer interp ile)
    pmin, pmax = min(height), max(height)
    txt_results.delete('1.0', tk.END)
    for i in range(3):
        y = pmin + (pmax-pmin)*(i+1)/3
        w = np.interp(y, height, load)*2
        txt_results.insert(tk.END,
            f"%{(i+1)*33}: Height={y:.2f} mm, Load={w:.2f} kg\n")
    cx = ((jmax-jmin)/3)*2 + jmin
    cw = max(load)*2
    txt_results.insert(tk.END,
        f"Çökme: Height={cx:.2f} mm, Load={cw:.2f} kg")

    # CSV panoya kopyalama için sakla
    global df_global
    df_global = df

def kopyala_csv():
    try:
        csv = df_global.to_csv(index=False)
        root.clipboard_clear()
        root.clipboard_append(csv)
        messagebox.showinfo("Tamamdır", "CSV panoya kopyalandı!")
    except:
        messagebox.showerror("Hata", "Önce 'Hesapla' butonuna bas!")

# GUI elemanları
root = tk.Tk(); root.title("Jack–Load Hesaplayıcı")

tk.Label(root, text="Height\tLoad (her satıra iki değer)").pack(anchor='w', padx=10)
txt_data = scrolledtext.ScrolledText(root, width=40, height=6)
txt_data.pack(padx=10, pady=5, fill='x')

frm = tk.Frame(root); frm.pack(padx=10, pady=5, fill='x')
tk.Label(frm, text="JackMin (mm):").grid(row=0, column=0)
entry_jmin = tk.Entry(frm, width=8); entry_jmin.grid(row=0, column=1)
tk.Label(frm, text="JackMax (mm):").grid(row=0, column=2)
entry_jmax = tk.Entry(frm, width=8); entry_jmax.grid(row=0, column=3)

btnf = tk.Frame(root); btnf.pack(pady=5)
tk.Button(btnf, text="Hesapla", command=hesapla).pack(side='left', padx=5)
tk.Button(btnf, text="CSV'yi Panoya Kopyala", command=kopyala_csv).pack(side='left', padx=5)
tk.Button(btnf, text="Çık", command=root.destroy).pack(side='left', padx=5)

tree = ttk.Treeview(root, show='headings')
tree.pack(padx=10, pady=5, expand=True, fill='both')

txt_results = scrolledtext.ScrolledText(root, width=40, height=4)
txt_results.pack(padx=10, pady=5, fill='x')

root.mainloop()
