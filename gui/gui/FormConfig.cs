using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Windows.Forms;

namespace gui
{
    public partial class FormConfig : Form
    {
        private FormLogin loginForm;
        public FormConfig(FormLogin loginForm)
        {
            this.loginForm = loginForm;
            InitializeComponent();
        }

        private void FormConfig_FormClosing(object sender, FormClosingEventArgs e)
        {
            if (e.CloseReason == CloseReason.UserClosing)
            {
                e.Cancel = true;
                Properties.Settings.Default.Reload();
                this.Hide();
            }
        }

        private void buttonSave_Click(object sender, EventArgs e)
        {
            Properties.Settings.Default.Save();
            if (this.loginForm.backendRunning)
            {
                this.loginForm.backendRunning = false;
                this.loginForm.backendRunning = true;
            }
        }

        private void buttonReset_Click(object sender, EventArgs e)
        {
            Properties.Settings.Default.Reload();
        }
    }
}
