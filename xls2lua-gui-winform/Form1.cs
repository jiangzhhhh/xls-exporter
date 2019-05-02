using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

namespace gui_win
{
    public partial class Form1 : Form
    {
        delegate void SetTextDelegate(string text);
        SetTextDelegate setTitle;

        public Form1()
        {
            InitializeComponent();
            setTitle = new SetTextDelegate(SetTitle);
        }

        private void SetTitle(string text)
        {
            this.Text = text;
        }

        private void Form1_DragEnter(object sender, DragEventArgs e)
        {
            e.Effect = DragDropEffects.Copy;
        }

        private void Form1_DragDrop(object sender, DragEventArgs e)
        {
            const string xls2lua = "xls2lua.exe";
            string[] files = (string[])e.Data.GetData(DataFormats.FileDrop);
            int suc = 0;
            int done = 0;
            int all = files.Length;
            foreach (string file in files)
            {
                ProcessStartInfo startInfo = new ProcessStartInfo
                {
                    FileName = xls2lua,
                    Arguments = string.Format("\"{0}\" \"{1}\"", file, Path.ChangeExtension(file, "lua")),
                    CreateNoWindow = true,
                    UseShellExecute = false,
                    RedirectStandardError = true,
                };
                try
                {
                    var ps = Process.Start(startInfo);
                    ps.EnableRaisingEvents = true;
                    ps.Exited += (object sender2, EventArgs e2) =>
                    {
                        done++;
                        if (ps.ExitCode != 0)
                        {
                            string output = ps.StandardError.ReadToEnd();
                            MessageBox.Show(output, $"出错啦：{file}");
                        }
                        else
                            suc++;
                        ps.Dispose();

                        if (done >= all)
                            this.Invoke(setTitle, $"导表[{suc}/{all}]");
                    };
                }
                catch (System.ComponentModel.Win32Exception)
                {
                    MessageBox.Show("找不到xls2lua.exe");
                }
            }
        }
    }
}
