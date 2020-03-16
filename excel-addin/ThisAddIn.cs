using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Xml.Linq;
using Excel = Microsoft.Office.Interop.Excel;
using Office = Microsoft.Office.Core;
using Microsoft.Office.Tools.Excel;
using System.IO;

namespace excel_addin
{
    public partial class ThisAddIn
    {
        public string ToolsDir {
            get {
                var bookPath = Globals.ThisAddIn.Application.ActiveWorkbook.FullName;
                var workDir = Path.GetDirectoryName(bookPath);
                return Path.Combine(workDir, "Tools");
            }
        }
        public string XlsExporter {
            get {
                return Path.Combine(ToolsDir, "xls-exporter");
            }
        }

        private void ThisAddIn_Startup(object sender, System.EventArgs e)
        {
            Globals.Ribbons.Ribbon1.tab1.Visible = true;
        }

        private void ThisAddIn_Shutdown(object sender, System.EventArgs e)
        {
        }

        #region VSTO 生成的代码

        /// <summary>
        /// 设计器支持所需的方法 - 不要修改
        /// 使用代码编辑器修改此方法的内容。
        /// </summary>
        private void InternalStartup()
        {
            this.Startup += new System.EventHandler(ThisAddIn_Startup);
            this.Shutdown += new System.EventHandler(ThisAddIn_Shutdown);
        }

        #endregion
    }
}
