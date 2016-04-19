using System;
using System.Linq;
using System.Text;
using System.IO;
using System.Diagnostics;
using System.Windows.Forms;

namespace gui
{
    class LiquidBackend : Process
    {
        // if > 0,  this process is running normally
        // if 0 , this process has failed
        // if -1, this process has stopped normally
        private int RemainRestartCount = -1;
        private StreamWriter LogFile;
        private FormLogin Parent;
        event EventHandler OnBalloonTip;

        public LiquidBackend(string Filename, FormLogin Parent)
        {
            this.Parent = Parent;
            this.StartInfo = new ProcessStartInfo(Filename);
            this.StartInfo.WindowStyle = ProcessWindowStyle.Hidden;
            this.StartInfo.CreateNoWindow = true;
            this.StartInfo.UseShellExecute = false;
            this.StartInfo.RedirectStandardError = true;
            this.StartInfo.RedirectStandardInput = true;
            this.StartInfo.RedirectStandardOutput = true;
            this.StartInfo.LoadUserProfile = false;
            this.EnableRaisingEvents = true;
            this.ErrorDataReceived += Backend_ErrorDataReceived;
            this.OutputDataReceived += Backend_OutputDataReceived;
            string logPath = Path.ChangeExtension(Filename, "log");
            File.Open(logPath, FileMode.OpenOrCreate, FileAccess.Write, FileShare.Read).Close();
            File.Delete(logPath + ".bak");
            File.Move(logPath, logPath + ".bak");
            this.LogFile = new StreamWriter(
                File.Open(logPath, FileMode.OpenOrCreate, FileAccess.Write, FileShare.Read));
            this.LogFile.AutoFlush = true;
        }

        public bool Running
        {
            get
            {
                return !this.HasExited && this.RemainRestartCount > 0;
            }
        }

        public new bool Start()
        {
            this.RemainRestartCount = 5;
            this.Exited += AutoRestart;
            if (base.Start())
            {
                try { this.BeginOutputReadLine(); }
                catch (Exception) { }
                try { this.BeginErrorReadLine(); }
                catch (Exception) { }
                return true;
            }
            else
            {
                return false;
            }
        }

        public void Stop()
        {
            this.Exited -= AutoRestart;
            this.Kill();
            this.RemainRestartCount = -1;
        }

        public void Reload()
        {
            if (!this.HasExited)
            {
                this.Stop();
                this.Start();
            }
            else if (this.RemainRestartCount == 0)
            {
                this.Start();
            }
        }

        private void AutoRestart(object sender, EventArgs e)
        {
            --RemainRestartCount;
            foreach (Process proc in Process.GetProcessesByName(this.StartInfo.FileName))
            {
                proc.Kill();
            }
            if (RemainRestartCount > 0)
            {
                base.Start();
            }
        }

        private void RaiseOnBalloonTip(OnBalloonTipEventArgs e)
        {
            EventHandler handler = OnBalloonTip;
            if (handler != null)
            {
                handler(this, e);
            }
        }

        private void Backend_OutputDataReceived(object sender, DataReceivedEventArgs e)
        {
            Backend_ErrorDataReceived(sender, e);
            if (String.IsNullOrWhiteSpace(e.Data)) return;
            Parent.ShowBalloonTip(1, "", e.Data, ToolTipIcon.None);
        }

        private void Backend_ErrorDataReceived(object sender, DataReceivedEventArgs e)
        {
            LogFile.WriteLine(e.Data);
        }
    }

    class OnBalloonTipEventArgs : EventArgs
    {
        public OnBalloonTipEventArgs(int timeout, string tipTitle, string tipText, ToolTipIcon tipIcon);
        public int timeout;
        public string tipTitle;
        public string tipText;
        public ToolTipIcon tipIcon; 
    }
}
