using Microsoft.Office.Interop.Excel;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;

using CheckBox = System.Windows.Forms.CheckBox;

namespace excel_addin
{
    public partial class SheetListForm : Form
    {
        public SheetListForm()
        {
            InitializeComponent();

            var sheets = Globals.ThisAddIn.Application.ActiveWorkbook.Worksheets.Cast<Worksheet>();
            foreach (var sheet in sheets)
            {
                var name = sheet.Name;

                var lvi = new ListViewItem(new[] { name, "" });
                this.listView1.Items.Add(lvi);

                var toggle = new SwitchToggle();
                this.listView1.Controls.Add(toggle);
                toggle.Checked = !name.StartsWith("=");
                toggle.CheckedChanged += (sender, args) => { ChangeWorkSheetExportable(lvi, sheet, (sender as CheckBox).Checked); };

                var rect = this.listView1.GetItemRect(0);
                toggle.Location = lvi.SubItems[1].Bounds.Location;
                toggle.Size = new Size(this.listView1.Columns[1].Width, rect.Height);
            }

            this.listView1.ColumnWidthChanging += ListView1_ColumnWidthChanging;
        }

        private void ListView1_ColumnWidthChanging(object sender, ColumnWidthChangingEventArgs e)
        {
            e.NewWidth = ((ListView)sender).Columns[e.ColumnIndex].Width;
            e.Cancel = true;
        }

        private void ChangeWorkSheetExportable(ListViewItem lvi, Worksheet ws, bool exportable)
        {
            if (exportable)
            {
                if (ws.Name.StartsWith("="))
                {
                    ws.Name = ws.Name.TrimStart('=');
                    lvi.SubItems[0].Text = ws.Name;
                }
            }
            else
            {
                if (!ws.Name.StartsWith("="))
                {
                    ws.Name = "=" + ws.Name;
                    lvi.SubItems[0].Text = ws.Name;
                }
            }
        }
    }
}
