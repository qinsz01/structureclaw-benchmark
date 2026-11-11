// Windows analysis.pythonBin launcher. It forwards original bytes and the
// actual child exit code; the existing Sclaw worker timeout owns the process tree.
using System;
using System.Diagnostics;
using System.IO;
using System.Threading.Tasks;

public static class CaptureWorkerLauncher
{
    public static int Main(string[] args)
    {
        try
        {
            if (args.Length != 1) throw new ArgumentException("Expected one original worker.py path");
            string python = Environment.GetEnvironmentVariable("SCLAW_BENCH_PYTHON");
            string worker = Path.GetFullPath(args[0]);
            string wrapper = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "capture_structureclaw_worker_v32.py");
            if (String.IsNullOrWhiteSpace(python) || !File.Exists(python) || !File.Exists(worker) || !File.Exists(wrapper))
                throw new FileNotFoundException("Pinned Python, capture wrapper and original worker must exist");
            // Quotes are illegal in Windows file names. No shell or arbitrary
            // argument string is used, and both arguments end in a file name.
            if (worker.IndexOf('"') >= 0 || wrapper.IndexOf('"') >= 0)
                throw new ArgumentException("Invalid worker file name");
            var start = new ProcessStartInfo(python, "\"" + wrapper + "\" \"" + worker + "\"");
            start.UseShellExecute = false;
            start.CreateNoWindow = true;
            start.RedirectStandardInput = true;
            start.RedirectStandardOutput = true;
            start.RedirectStandardError = true;
            using (var child = Process.Start(start))
            {
                Task input = Task.Run(() => {
                    try { Console.OpenStandardInput().CopyTo(child.StandardInput.BaseStream); }
                    finally { child.StandardInput.BaseStream.Close(); }
                });
                Task output = child.StandardOutput.BaseStream.CopyToAsync(Console.OpenStandardOutput());
                Task error = child.StandardError.BaseStream.CopyToAsync(Console.OpenStandardError());
                child.WaitForExit();
                Task.WaitAll(input, output, error);
                return child.ExitCode;
            }
        }
        catch (Exception error)
        {
            Console.Error.WriteLine("CAPTURE_LAUNCH_FAILED: " + error.Message);
            return 2;
        }
    }
}
