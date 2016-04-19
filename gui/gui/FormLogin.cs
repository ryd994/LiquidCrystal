using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Net;
using System.Windows.Forms;
using System.Diagnostics;
using System.IO;

namespace gui
{
    public partial class FormLogin : Form
    {
        private FormConfig formConfig1;
        private StreamWriter logFile;
        private LiquidBackend backend;
        
        public FormLogin()
        {
            InitializeComponent();
            this.formConfig1 = new FormConfig(this);

            //Backup old log, then open new
            try 
            {
                backend = new LiquidBackend("lqdcrysd.exe", this);
            }
            catch (IOException)
            {
                MessageBox.Show("无法开日志文件", "启动失败", MessageBoxButtons.OK, MessageBoxIcon.Error);
                Application.Exit();
            }
        }

        private void ShowBalloonTip(object sender, OnBalloonTipEventArgs e)
        {
            this.notifyIcon1.ShowBalloonTip(e.timeout, e.tipTitle, e.tipText, e.tipIcon);
        }

        internal bool backendRunning
        {
            get
            {
                backend.Refresh();
                return !backend.HasExited;
            }
            set
            {
                // this method controls running of backend process and text of tray menu
                // True for turn on and False for turn off
                if (value)
                {
                    this.ToolStripMenuItemLogout.Text = "注销";
                    this.notifyIcon1.Text = "127.0.0.1:" + Properties.Settings.Default.PortNum;

                    //Start backend
                    backend.StartInfo.Arguments = String.Format("-p {0} -cs super.crystalacg.com -as {3}", Properties.Settings.Default.PortNum, Properties.Settings.Default.Username, Properties.Settings.Default.Password, Properties.Settings.Default.Server);
                    this.backend.EnableRaisingEvents = true;
                    this.backend.Start();
                    try
                    {
                        this.backend.BeginOutputReadLine();
                        this.backend.BeginErrorReadLine();
                    }
                    catch (System.InvalidOperationException) { }
                }
                else
                {
                    this.ToolStripMenuItemLogout.Text = "登入";
                    this.notifyIcon1.Text = "LiquidCrystal";
                    try
                    {
                        this.backend.EnableRaisingEvents = false;
                        this.backend.StandardInput.Close();
                        this.backend.CloseMainWindow();

                        // wait 1s for graceful shutdown
                        if (!this.backend.WaitForExit(1000))
                        {
                            // if not gracefully shutting-down, try kill backend process every 0.1s 
                            while (!this.backend.WaitForExit(100))
                            {
                                this.backend.Kill();
                            }
                        }
                        this.backend.Close();
                    }
                    catch (System.InvalidOperationException) { }
                }
            }
        }

        private void backend_Exited(object sender, EventArgs e)
        {
            // restart backend on abnormal exit
            // this is not triggered if closing with runBackend(false)
            if (backend.ExitCode != 0)
            {
                if (backend.ExitCode == 65)
                {

                    notifyIcon1.ShowBalloonTip(1, "启动失败", "无法打开端口，请尝试更换端口", ToolTipIcon.None);
                }
                System.Threading.Thread.Sleep(1000);
                backend.Start();
            }
        }

        private void notifyIcon1_MouseClick(object sender, MouseEventArgs e)
        {
            if (e.Button == MouseButtons.Left)
            {
                this.formConfig1.Visible = !this.formConfig1.Visible;
            }
        }

        private void ToolStripMenuItemLaunchConfig_Click(object sender, EventArgs e)
        {
            this.formConfig1.Show();
        }

        private void ToolStripMenuItemExit_Click(object sender, EventArgs e)
        {
            backendRunning = false;
            Application.Exit();
        }

        private void FormLogin_FormClosing(object sender, FormClosingEventArgs e)
        {
            if (e.CloseReason == CloseReason.UserClosing)
            {
                e.Cancel = true;
                this.Hide();
            }
        }

        private void ToolStripMenuItemLogin_Click(object sender, EventArgs e)
        {
            backendRunning = false;
            this.Show();
        }

        private void buttonLogin_Click(object sender, EventArgs e)
        {
            try
            {
                //disable login button to prevent mutiple click
                this.buttonLogin.Text = "……";
                this.buttonLogin.Enabled = false;

                // verify user-pass for 200 response
                WebRequest req = WebRequest.Create(String.Format("http://{0}/login", Properties.Settings.Default.Server));
                req.Credentials = new NetworkCredential(Properties.Settings.Default.Username, Properties.Settings.Default.Password);
                req.Proxy = null;

                // try get response, bad status code will also throw exception and be captured below
                HttpWebResponse resp = (HttpWebResponse)req.GetResponse();
                resp.Close();
                if (resp.StatusCode != HttpStatusCode.OK) {
                    throw new WebException("Bad HTTP status code:"+resp.StatusCode.ToString());
                }

                // Save settings and start backend
                Properties.Settings.Default.Save();
                notifyIcon1.ShowBalloonTip(1, "登入成功", "正在启动……", ToolTipIcon.None);
                backendRunning = true;
                this.Hide();
            }
            catch (WebException exception)
            {
                MessageBox.Show(exception.Message);
                // if there is an response received, show HTTP status code
                // else notify there is an error only
                if (exception.Response != null)
                {
                    HttpWebResponse resp = (HttpWebResponse)exception.Response;
                    switch (resp.StatusCode)
                    {
                        case HttpStatusCode.Forbidden:
                            notifyIcon1.ShowBalloonTip(1, "登入失败", "账号密码错误", ToolTipIcon.None);
                            break;
                        default:
                            notifyIcon1.ShowBalloonTip(1, "登入失败", resp.StatusCode.ToString(), ToolTipIcon.None);
                            break;
                    }
                    resp.Close();
                }
                else
                {
                    notifyIcon1.ShowBalloonTip(1, "无法连接到服务器", exception.Message, ToolTipIcon.None);
                }
                return;
            }
            finally
            {
                // re-enable button, refer to beginning of method
                buttonLogin.Text = "==》";
                buttonLogin.Enabled = true;
            }
        }

        private void FormLogin_Shown(object sender, EventArgs e)
        {
            // Auto login when program started
            //buttonLogin.PerformClick();
        }

    }
}
