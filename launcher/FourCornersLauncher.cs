using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using Microsoft.Win32;
using System.Windows.Forms;

internal static class FourCornersLauncher
{
    [STAThread]
    private static int Main(string[] args)
    {
        string stagedCue = null;
        byte[] cueBytes = null;
        bool createdCue = false;

        try
        {
            string tf2Root = ReadArgument(args, "--tf2-root");
            if (String.IsNullOrWhiteSpace(tf2Root))
                tf2Root = FindGame(LaunchConfig.HostAppId, "Team Fortress 2", "tf_win64.exe", "tf.exe");
            if (String.IsNullOrWhiteSpace(tf2Root))
                throw new InvalidOperationException("Team Fortress 2 was not found in the installed Steam libraries.");
            tf2Root = Path.GetFullPath(tf2Root);

            string tf2Exe = FindExecutable(tf2Root, "tf_win64.exe", "tf.exe");
            if (tf2Exe == null)
                throw new InvalidOperationException("The TF2 install folder passed by Melty does not contain the game executable.");

            string l4d2Root = FindGame(LaunchConfig.SourceAppId, "Left 4 Dead 2");
            if (l4d2Root == null)
                throw new InvalidOperationException("Left 4 Dead 2 was not found in the installed Steam libraries. The horde warning is read from your local L4D2 copy and is not bundled with this mashup.");

            string sourceCue = Path.Combine(l4d2Root, LaunchConfig.SourceRelativeAsset.Replace('/', Path.DirectorySeparatorChar));
            if (!File.Exists(sourceCue))
                throw new InvalidOperationException("The selected horde warning cue is missing from the installed Left 4 Dead 2 files.");

            stagedCue = Path.Combine(tf2Root, LaunchConfig.ModDirectory.Replace('/', Path.DirectorySeparatorChar), LaunchConfig.CueRelativeDestination.Replace('/', Path.DirectorySeparatorChar));
            cueBytes = File.ReadAllBytes(sourceCue);
            string cueDirectory = Path.GetDirectoryName(stagedCue);
            if (!Directory.Exists(cueDirectory))
                Directory.CreateDirectory(cueDirectory);

            if (File.Exists(stagedCue))
            {
                if (!File.ReadAllBytes(stagedCue).SequenceEqual(cueBytes))
                    throw new InvalidOperationException("A different file already uses the horde cue path in TF2's custom folder. I left it untouched.");
            }
            else
            {
                File.WriteAllBytes(stagedCue, cueBytes);
                createdCue = true;
            }

            var start = new ProcessStartInfo();
            start.FileName = tf2Exe;
            start.WorkingDirectory = tf2Root;
            start.Arguments = JoinArguments(LaunchConfig.GameArguments);
            start.UseShellExecute = false;
            start.CreateNoWindow = false;

            using (Process game = Process.Start(start))
            {
                if (game == null)
                    throw new InvalidOperationException("Windows could not start Team Fortress 2.");
                game.WaitForExit();
                return game.ExitCode;
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "Holdout: Four Corners", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
        finally
        {
            if (createdCue && stagedCue != null && cueBytes != null)
            {
                try
                {
                    if (File.Exists(stagedCue) && File.ReadAllBytes(stagedCue).SequenceEqual(cueBytes))
                        File.Delete(stagedCue);
                }
                catch
                {
                    // Preserve the game session; the audio file is player-owned and remains in the custom folder.
                }
            }
        }
    }

    private static string ReadArgument(string[] args, string name)
    {
        for (int i = 0; i + 1 < args.Length; i++)
            if (String.Equals(args[i], name, StringComparison.OrdinalIgnoreCase))
                return args[i + 1];
        return null;
    }

    private static string JoinArguments(string[] values)
    {
        return String.Join(" ", values.Select(QuoteArgument).ToArray());
    }

    private static string QuoteArgument(string value)
    {
        if (value.Length == 0)
            return "\"\"";
        if (!value.Any(Char.IsWhiteSpace) && value.IndexOf('"') < 0)
            return value;
        return "\"" + value.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
    }

    private static string FindExecutable(string root, params string[] names)
    {
        foreach (string name in names)
        {
            string path = Path.Combine(root, name);
            if (File.Exists(path))
                return path;
        }
        return null;
    }

    private static string FindGame(string appId, string folderName, params string[] markers)
    {
        foreach (string library in SteamLibraries())
        {
            string manifest = Path.Combine(library, "steamapps", "appmanifest_" + appId + ".acf");
            string game = Path.Combine(library, "steamapps", "common", folderName);
            if (!File.Exists(manifest) || !Directory.Exists(game))
                continue;
            if (markers.Length == 0 || markers.Any(marker => File.Exists(Path.Combine(game, marker))))
                return game;
        }
        return null;
    }

    private static IEnumerable<string> SteamLibraries()
    {
        var roots = new List<string>();
        string registered = ReadSteamPath(RegistryView.Registry64);
        if (String.IsNullOrEmpty(registered))
            registered = ReadSteamPath(RegistryView.Registry32);
        if (!String.IsNullOrEmpty(registered))
            roots.Add(registered);
        roots.Add(@"C:\Program Files (x86)\Steam");
        roots.Add(@"C:\Program Files\Steam");

        var libraries = new List<string>();
        foreach (string root in roots.Where(Directory.Exists))
        {
            AddUnique(libraries, root);
            string file = Path.Combine(root, "steamapps", "libraryfolders.vdf");
            if (!File.Exists(file))
                continue;

            string content = File.ReadAllText(file);
            foreach (Match match in Regex.Matches(content, "\"path\"\\s+\"([^\"]+)\"", RegexOptions.IgnoreCase))
            {
                string path = match.Groups[1].Value.Replace("\\\\", "\\");
                if (Directory.Exists(path))
                    AddUnique(libraries, path);
            }
        }
        return libraries;
    }

    private static string ReadSteamPath(RegistryView view)
    {
        try
        {
            using (RegistryKey key = RegistryKey.OpenBaseKey(RegistryHive.CurrentUser, view).OpenSubKey(@"Software\Valve\Steam"))
                return key == null ? null : key.GetValue("SteamPath") as string;
        }
        catch
        {
            return null;
        }
    }

    private static void AddUnique(List<string> values, string path)
    {
        if (!values.Any(value => String.Equals(value, path, StringComparison.OrdinalIgnoreCase)))
            values.Add(path);
    }
}
