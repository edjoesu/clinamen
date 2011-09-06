using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Data.SqlTypes;
using System.Drawing;
using System.Text;
using System.Windows.Forms;
using System.IO;
using System.Runtime.Serialization.Formatters.Binary;
using DataStructures;
using MySql.Data;
using MySql.Data.MySqlClient;
using MySql.Data.Types;

namespace Elgin
{
    public partial class ElginTrackerForm : Form
    {
        public class MySQLHandler
        {
            
            public MySqlConnection conn;

            public MySQLHandler() {
                string connStr = "server=bec2.mit.edu;user=root;database=filelist;port=3306;password=password;";
                this.conn = new MySqlConnection(connStr);
                try
                {   
                    conn.Open();
                }
                catch (Exception ex) 
                {
                    MessageBox.Show("Unable to open database connection due to exception: " + ex.Message + ex.StackTrace);
                }
            }
            public void CloseConnection() {
                conn.Close();
            }
            public void ExecuteNonQuery(string sql) {  
                MySqlCommand cmd = new MySqlCommand(sql, this.conn);
                try
                {   
                    cmd.ExecuteNonQuery();
                }
                catch (Exception ex) 
                {
                    MessageBox.Show("Unable to execute command due to exception: " + ex.Message + ex.StackTrace);
                }
            }
            public void addRunLog(string fileName, RunLog log)
            {
                MySqlCommand cmdq = new MySqlCommand(@"SELECT path FROM filelist_runloginfo WHERE path=@path", this.conn);
                cmdq.Parameters.AddWithValue("@path", fileName);

                object result = cmdq.ExecuteScalar();

                if (result == null)
                {
                    MySqlCommand cmd = new MySqlCommand(@"INSERT IGNORE INTO filelist_runloginfo 
                         (path, loc_key, time, sequencepath, listiterationnumber, liststarttime, sequenceduration, description) 
                         VALUES (@path, @loc_key, @time, @sequencepath, @listiterationnumber, @liststarttime, @sequenceduration, @description)", this.conn);

                    cmd.Parameters.AddWithValue("@path", fileName);
                    cmd.Parameters.AddWithValue("@loc_key", "default");
                    cmd.Parameters.AddWithValue("@time", log.RunTime);
                    cmd.Parameters.AddWithValue("@sequencepath", log.SequenceFileName);
                    cmd.Parameters.AddWithValue("@listiterationnumber", log.RunSequence.ListIterationNumber);
                    cmd.Parameters.AddWithValue("@liststarttime", log.ListStartTime);
                    cmd.Parameters.AddWithValue("@sequenceduration", log.RunSequence.SequenceDuration);
                    cmd.Parameters.AddWithValue("@description", log.RunSequence.SequenceDescription);

                    cmd.ExecuteNonQuery();

                    this.addVariables(fileName, log);
                }
            }
            public void addVariables(string fileName, RunLog log)
            {
                foreach (Variable var in log.RunSequence.Variables) {
                    MySqlCommand cmd = new MySqlCommand(@"INSERT INTO filelist_variablevalue
                       (name, value, runlog_id) 
                       VALUES (@name, @value, @runlog)", this.conn);

                    cmd.Parameters.AddWithValue("@name", var.VariableName);
                    cmd.Parameters.AddWithValue("@value", var.VariableValue);
                    cmd.Parameters.AddWithValue("@runlog", fileName);

                    cmd.ExecuteNonQuery();
                }
            }
        }
        public class DataGridColumnWrapper
        {
            public DataGridViewColumn column;
            public override string ToString()
            {
                return column.HeaderText;
            }
            public DataGridColumnWrapper(DataGridViewColumn col) {
                this.column = col;
            }
        }

        public class ColumnVariableSelection
        {
            public string name;
            public int id;
            /// <summary>
            /// True if selected by name. False if selected by ID.
            /// </summary>
            public bool usingName;

            public ColumnVariableSelection(string name)
            {
                this.name = name;
                this.usingName = true;
            }

            public ColumnVariableSelection(int id)
            {
                this.id = id;
                this.usingName = false;
            }
        }

        private Dictionary<DataGridViewColumn, ColumnVariableSelection> variableSelections;

        private List<DataGridViewColumn> variableColumns;

        private DataGridViewColumn lastMouseEnterOverColumn;

        private Dictionary<RunLog, RunLogExplorerForm> openLogs;

        public ElginTrackerForm()
        {
            InitializeComponent();
            openLogs = new Dictionary<RunLog, RunLogExplorerForm>();

            System.Diagnostics.Process proc;
            proc = new System.Diagnostics.Process();

            foreach (DataGridViewColumn col in dataGridView1.Columns)
            {
                columnVisibility.Items.Add(new DataGridColumnWrapper(col));
                columnVisibility.SetItemChecked(columnVisibility.Items.Count - 1, col.Visible);
            }

            variableColumns = new List<DataGridViewColumn>();
            variableColumns.Add(VarA);
            variableColumns.Add(VarB);
            variableColumns.Add(VarC);
            variableColumns.Add(VarD);
            variableColumns.Add(VarE);
            variableColumns.Add(VarF);
            variableColumns.Add(VarG);

            variableSelections = new Dictionary<DataGridViewColumn, ColumnVariableSelection>();

        }

        public void CloseAllBrowsers()
        {
            List<RunLog> logs = new List<RunLog>();
            logs.AddRange(openLogs.Keys);
            foreach (RunLog log in logs)
            {
                closeLog(log);
            }
            updateOpenLogList();
        }

        private void closeLog(RunLog log)
        {
            if (log == null) return;
            if (openLogs.ContainsKey(log))
            {
                openLogs[log].Close();
                openLogs.Remove(log);
            }
        }

        public void MinimizeAll()
        {
            this.MdiParent.SuspendLayout();
            foreach (RunLogExplorerForm rlf in openLogs.Values)
            {
                rlf.SuspendLayout();
            }

            foreach (RunLogExplorerForm rlf in openLogs.Values)
            {
                rlf.WindowState = FormWindowState.Minimized;
            }

            foreach (RunLogExplorerForm rlf in openLogs.Values)
            {
                rlf.ResumeLayout();
            }

            this.MdiParent.ResumeLayout();
        }

        private void updateOpenLogList()
        {
            dataGridView1.Rows.Clear();
            foreach (RunLog rlg in openLogs.Keys)
            {
                addLogToDataGrid(rlg);
            }
        }

        private string getVariableString(DataGridViewColumn variableColumn, RunLog rlg)
        {
            if (variableSelections.ContainsKey(variableColumn))
            {
                if (variableSelections[variableColumn].usingName)
                {
                    Variable var = rlg.RunSequence.getVariable(variableSelections[variableColumn].name);
                    if (var != null)
                    {
                        return var.VariableValue.ToString();
                    }
                    else return "Undefined";
                }
                else
                {
                    Variable var = rlg.RunSequence.getVariable(variableSelections[variableColumn].id);
                    if (var != null)
                    {
                        return var.VariableValue.ToString();
                    }
                    else return "Undefined";
                }
            }
            else
            {
                return "Unassigned";
            }
        }

        private void addLogToDataGrid(RunLog rlg)
        {



            dataGridView1.Rows.Add(new object[] { 
                null,                                   // close button
                rlg,                        // sequence name
                rlg.RunSequence.ListIterationNumber,    // seq iteration  
                rlg.RunTime,                            // seq start time
                rlg.ListStartTime,                      // list start time
                rlg.RunSequence.SequenceDuration,       // seq duration
                rlg.RunSequence.CalibrationShot.ToString(), // calib shot?
                getVariableString(VarA, rlg),                // Variables A through G
                getVariableString(VarB, rlg),
                getVariableString(VarC, rlg),
                getVariableString(VarD, rlg),
                getVariableString(VarE, rlg),
                getVariableString(VarF, rlg),
                getVariableString(VarG, rlg)
            });
        }

        public void openFile(object sender, EventArgs e)
        {
            OpenFileDialog fileDialog = new OpenFileDialog();

            fileDialog.Title = "Open RunLog File(s)";
            fileDialog.Filter = "RunLog files (*.clg)|*.clg|All files (*.*)|*.*";
            fileDialog.FilterIndex = 1;
            fileDialog.Multiselect = true;

            DialogResult result = fileDialog.ShowDialog();

            string[] fileNames = fileDialog.FileNames;

            if (result == DialogResult.OK) {
                loadFiles(fileNames);
            }

        }

        public void addFileToDB(object sender, EventArgs e)
        {
            OpenFileDialog fileDialog = new OpenFileDialog();

            fileDialog.Title = "Open RunLog File(s)";
            fileDialog.Filter = "RunLog files (*.clg)|*.clg|All files (*.*)|*.*";
            fileDialog.FilterIndex = 1;
            fileDialog.Multiselect = true;

            DialogResult result = fileDialog.ShowDialog();

            string[] fileNames = fileDialog.FileNames;
            string fileDirectory = fileDialog.InitialDirectory;

            if (result == DialogResult.OK)
            {
                addFilesFromList(fileNames, fileDirectory);
            }

        }

        public void addFilesFromList(string[] fileNames, string fileDirectory)
        {
            MySQLHandler handler = new MySQLHandler();
            foreach (string fileName in fileNames)
            {
                try
                {
                    FileStream fs = new FileStream(fileName, FileMode.Open, FileAccess.Read, FileShare.None);
                    BinaryFormatter bf = new BinaryFormatter();
                    RunLog log = (RunLog)bf.Deserialize(fs);  
                    handler.addRunLog(fileName, log);
                    fs.Close();
                }
                catch (Exception ex)
                {
                    MessageBox.Show("Unable to open or read file " + fileName + " due to exception: " + ex.Message + ex.StackTrace);
                }
            }
            handler.CloseConnection();
        }

        public void loadFiles(string[] fileNames)
        {
            foreach (string fileName in fileNames)
            {
                try
                {
                    FileStream fs = new FileStream(fileName, FileMode.Open, FileAccess.Read, FileShare.None);
                    BinaryFormatter bf = new BinaryFormatter();
                    RunLog log = (RunLog)bf.Deserialize(fs);
                    RunLogExplorerForm explorer = new RunLogExplorerForm(log, fileName);
                    explorer.MdiParent = this.MdiParent;
                    explorer.FormClosed += new FormClosedEventHandler(explorer_FormClosed);
                    explorer.Show();
                    openLogs.Add(log, explorer);
                }
                catch (Exception ex)
                {
                    MessageBox.Show("Unable to open or read file " + fileName + " due to exception: " + ex.Message + ex.StackTrace);
                }
            }
            updateOpenLogList();
        }

        void explorer_FormClosed(object sender, FormClosedEventArgs e)
        {
            List<RunLog> logs = new List<RunLog>();
            logs.AddRange(openLogs.Keys);
            foreach (RunLog rlg in logs)
            {
                if (openLogs[rlg] == sender)
                {
                    openLogs.Remove(rlg);
                    break;
                }
            }
            updateOpenLogList();
        }

        private void ElginMainForm_Load(object sender, EventArgs e)
        {

        }

        private void dataGridView1_CellContentClick(object sender, DataGridViewCellEventArgs e)
        {
            if (e.ColumnIndex == -1)
                return;


            if (dataGridView1.Columns[e.ColumnIndex] == CloseButton)
            {
                if (e.RowIndex == -1)
                    return;
                RunLog rlg = dataGridView1.Rows[e.RowIndex].Cells[SeqName.Index].Value as RunLog;
                closeLog(rlg);
                updateOpenLogList();
            }
        }

        private void columnVisibility_SelectedIndexChanged(object sender, EventArgs e)
        {
           /* List<DataGridViewColumn> visibleColunms = new List<DataGridViewColumn>();
            foreach (Object obj in columnVisibility.CheckedItems)
            {
                DataGridColumnWrapper wrap = obj as DataGridColumnWrapper;
                if (wrap != null)
                {
                    visibleColunms.Add(wrap.column);
                }
            }
            foreach (DataGridViewColumn col in dataGridView1.Columns)
            {
                if (visibleColunms.Contains(col))
                    col.Visible = true;
                else
                    col.Visible = false;
            }

            dataGridView1.Refresh();*/
        }

        private void columnVisibility_ItemCheck(object sender, ItemCheckEventArgs e)
        {
            Object obj = columnVisibility.Items[e.Index];
            DataGridColumnWrapper wrap = obj as DataGridColumnWrapper;
            if (wrap == null)
                return;
            if (e.NewValue == CheckState.Checked)
                wrap.column.Visible = true;
            else
                wrap.column.Visible = false;
        }

        private void varNameSelector_DropDown(object sender, EventArgs e)
        {
            varNameSelector.Items.Clear();
            List<string> variableNames = new List<string>();
            foreach (RunLog rlg in openLogs.Keys)
            {
                foreach (Variable var in rlg.RunSequence.Variables)
                {
                    if (!variableNames.Contains(var.VariableName))
                    {
                        variableNames.Add(var.VariableName);
                    }
                }
            }
            varNameSelector.Items.AddRange(variableNames.ToArray());
        }

        private void varNumSelector_DropDown(object sender, EventArgs e)
        {
            varNumSelector.Items.Clear();
            int maxID = 0;
            foreach (RunLog rlg in openLogs.Keys)
            {
                if (rlg.RunSequence.Variables.Count > maxID)
                    maxID = rlg.RunSequence.Variables.Count;
            }
            for (int i = 1; i <= maxID; i++)
            {
                varNumSelector.Items.Add(i);
            }
        }


        private void dataGridView1_CellMouseEnter(object sender, DataGridViewCellEventArgs e)
        {
            if (e.ColumnIndex == -1) return;
            lastMouseEnterOverColumn = dataGridView1.Columns[e.ColumnIndex];
        }

        private void unassignToolStripMenuItem_Click(object sender, EventArgs e)
        {
            if (variableSelections.ContainsKey(lastMouseEnterOverColumn))
            {
                variableSelections.Remove(lastMouseEnterOverColumn);
            }
            dataGridView1.Refresh();
            refreshVariables();
        }

        private void varNameSelector_DropDownClosed(object sender, EventArgs e)
        {
            string selectedName = varNameSelector.SelectedItem as string;
            if (selectedName == null)
                return;
            if (variableSelections.ContainsKey(lastMouseEnterOverColumn)) {
                variableSelections.Remove(lastMouseEnterOverColumn);
            }
            variableSelections.Add(lastMouseEnterOverColumn, new ColumnVariableSelection(selectedName));
            refreshVariables();
            variableColumnSettingsStrip.Close();
            varNameSelector.SelectedItem = null;
        }

        private void varNumSelector_DropDownClosed(object sender, EventArgs e)
        {
            if (!(varNumSelector.SelectedItem is int))
                return;
            int selectedInt = (int) varNumSelector.SelectedItem;

            if (variableSelections.ContainsKey(lastMouseEnterOverColumn))
            {
                variableSelections.Remove(lastMouseEnterOverColumn);
            }
            variableSelections.Add(lastMouseEnterOverColumn, new ColumnVariableSelection(selectedInt));
            refreshVariables();
            variableColumnSettingsStrip.Close();
            varNumSelector.SelectedItem = null;
        }

        private void refreshVariables()
        {
            foreach (DataGridViewColumn col in variableColumns)
            {
                if (variableSelections.ContainsKey(col)) {
                    if (variableSelections[col].usingName)
                    {
                        col.HeaderText = "[" + variableSelections[col].name + "]";
                    }
                    else
                    {
                        col.HeaderText = "Variable #" + variableSelections[col].id;
                    }
                }
                else {
                    col.HeaderText = "Unassigned Var.";
                }
            }
            columnVisibility.Refresh();

            updateOpenLogList();
        }


    }
}