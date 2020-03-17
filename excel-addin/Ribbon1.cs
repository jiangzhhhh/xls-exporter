using Microsoft.Office.Interop.Excel;
using Microsoft.Office.Tools.Ribbon;
using System;
using System.Collections.Generic;
using System.Deployment.Application;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Windows.Forms;

namespace excel_addin
{
    public partial class Ribbon1
    {
        string Targetlang {
            get {
                return Globals.Ribbons.Ribbon1.gallery1.SelectedItem.Label;
            }
        }
        private void Ribbon1_Load(object sender, RibbonUIEventArgs e)
        {
            Globals.Ribbons.Ribbon1.gallery1.Label = $"{Targetlang}";

            var revision = ApplicationDeployment.CurrentDeployment.CurrentVersion.ToString(4);
            Globals.Ribbons.Ribbon1.label2.Label = $"版本:{revision}";
        }

        void Export(string[] files, string[] outfiles)
        {
            bool singleMode = files.Length == 1;
            var prog = Globals.ThisAddIn.XlsExporter;
            int done = 0;
            int suc = 0;
            int all = files.Length;
            for (int i = 0; i < all; ++i)
            {
                var file = files[i];
                var tofile = outfiles[i];

                ProcessStartInfo startInfo = new ProcessStartInfo
                {
                    FileName = prog,
                    Arguments = $"\"{file}\" -o \"{tofile}\" -l {Targetlang}",
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
                        int exitCode = ps.ExitCode;
                        if (exitCode == 0)
                            suc++;
                        bool allDone = done == all;

                        if (exitCode != 0)
                        {
                            string output = ps.StandardError.ReadToEnd();
                            if (singleMode)
                                ParseErrorFeedback(output);
                            else
                                MessageBox.Show(output, $"出错啦：{file}");
                        }
                        ps.Dispose();

                        if (allDone)
                        {
                            if (suc == all)
                                SetStatusText("完成啦");
                            else if (!singleMode)
                                SetStatusText("全部执行完毕,有部分表格失败");
                        }
                    };
                }
                catch (System.ComponentModel.Win32Exception)
                {
                    MessageBox.Show("找不到xls-exporter");
                    return;
                }
            }
        }

        void SetStatusText(string msg)
        {
            Globals.Ribbons.Ribbon1.label1.Label = msg;
        }

        private void button3_Click(object sender, RibbonControlEventArgs e)
        {
            var form = new SheetListForm();
            form.ShowDialog();
        }

        void ParseErrorFeedback(string err)
        {
            var splited = err.Replace("\r\n", "\n");
            var lines = splited.Split('\n');

            string[] keys = new string[] { "error", "title", "detail", "sheet", "row", "col" };
            Dictionary<string, string> info = new Dictionary<string, string>();
            foreach (var line in lines)
            {
                foreach (var key in keys)
                {
                    if (line.StartsWith(key))
                    {
                        var value = line.Substring(key.Length + 1).TrimEnd('\n');
                        Debug.WriteLine($"{key}:{value}");
                        info[key] = value;
                    }
                }
            }
            if (info.TryGetValue("error", out var error))
            {
                var sheet = info["sheet"];
                var row = info["row"];
                var col = info["col"];
                var ws = Globals.ThisAddIn.Application.ActiveWorkbook.Worksheets[sheet] as Worksheet;
                ws.Activate();
                var range = ws.Range[col + row];
                range.Activate();
                MessageBox.Show(info["detail"], info["title"]);
            }
            else
            {
                MessageBox.Show(err, "internal exception");
            }
        }

        private void button4_Click(object sender, RibbonControlEventArgs e)
        {
            var prog = Globals.ThisAddIn.XlsExporter;
            var activeBook = Globals.ThisAddIn.Application.ActiveWorkbook;
            var file = activeBook.FullName;
            ProcessStartInfo startInfo = new ProcessStartInfo
            {
                FileName = prog,
                Arguments = $"-l {Targetlang} \"{file}\" --check",
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
                    int exitCode = ps.ExitCode;
                    if (exitCode != 0)
                    {
                        string output = ps.StandardError.ReadToEnd();
                        ParseErrorFeedback(output);
                    }
                    else
                    {
                        Globals.Ribbons.Ribbon1.label1.Label = "一切正常";
                    }
                    ps.Dispose();
                };
            }
            catch (System.ComponentModel.Win32Exception)
            {
                MessageBox.Show("找不到找不到xls-exporter");
                return;
            }
        }

        private void button5_Click(object sender, RibbonControlEventArgs e)
        {
            var activeBook = Globals.ThisAddIn.Application.ActiveWorkbook;
            var bookDir = Path.GetDirectoryName(activeBook.FullName);
            var dataDir = Path.Combine(bookDir, "Data");
            if (!Directory.Exists(dataDir))
                dataDir = bookDir;
            var outfile = Path.Combine(dataDir, Path.ChangeExtension(activeBook.Name, $".{Targetlang}"));
            Debug.WriteLine(outfile);
            if (File.Exists(outfile))
                Process.Start("explorer", $"/select,\"{outfile}\"");
            else
                Process.Start("explorer", $"\"{dataDir}\"");
        }

        private void splitButton1_Click(object sender, RibbonControlEventArgs e)
        {
            var activeBook = Globals.ThisAddIn.Application.ActiveWorkbook;
            var bookDir = Path.GetDirectoryName(activeBook.FullName);
            var dataDir = Path.Combine(bookDir, "Data");
            if (!Directory.Exists(dataDir))
                dataDir = bookDir;
            SaveFileDialog dialog = new SaveFileDialog();
            dialog.FileName = Path.ChangeExtension(activeBook.Name, $".{Targetlang}");
            dialog.InitialDirectory = dataDir;
            dialog.Filter = $"{Targetlang} files (*.{Targetlang})|*.{Targetlang}";
            dialog.FilterIndex = 2;
            dialog.RestoreDirectory = true;
            if (dialog.ShowDialog() == DialogResult.OK)
            {
                var outPath = dialog.FileName;
                Export(new[] { activeBook.FullName }, new[] { outPath });
            }
        }

        private void button6_Click(object sender, RibbonControlEventArgs e)
        {
            var activeBook = Globals.ThisAddIn.Application.ActiveWorkbook;
            var bookDir = Path.GetDirectoryName(activeBook.FullName);
            var dataDir = Path.Combine(bookDir, "Data");
            if (!Directory.Exists(dataDir))
                dataDir = bookDir;
            FolderBrowserDialog dialog = new FolderBrowserDialog();
            dialog.SelectedPath = dataDir;
            dialog.Description = "输出到文件夹";
            if (dialog.ShowDialog() == DialogResult.OK)
            {
                var saveDir = dialog.SelectedPath;
                var files = Directory.GetFiles(bookDir, "*.xl*", SearchOption.TopDirectoryOnly)
                    .Where(x => !Path.GetFileName(x).StartsWith("~$"))    //过滤临时文件
                    .ToArray();
                var tofiles = files.Select(x => Path.Combine(saveDir, Path.ChangeExtension(Path.GetFileName(x), ".lua"))).ToArray();
                Export(files, tofiles);
            }
        }

        private void gallery1_Click(object sender, RibbonControlEventArgs e)
        {
            Globals.Ribbons.Ribbon1.gallery1.Label = $"{Targetlang}";
        }
    }
}
