from flmeshing import FLMeshing
import os
import subprocess
import re

regions = ['flredecomp', 'flredecomp::gmsh_read', 'flredecomp::state', 'flredecomp::zoltan']

re_flredecomp = re.compile(r"\/flredecomp\s+::\s+([0-9\.]+)")
re_io_gmsh = re.compile(r"I\/O\s+::\s+Gmsh\s+::\s+([0-9\.]+)")
re_flrd_state = re.compile(r"\/flredecomp\s+::\s+Populate State\s+::\s+([0-9\.]+)")
re_flrd_zoltan = re.compile(r"\/flredecomp\s+::\s+zoltan\_drive\s+::\s+([0-9\.]+)")

class FLRedecompMeshing(FLMeshing):
    benchmark = 'flredecomp'
    description = 'Fluidity flredecomp benchmark'

    method = 'flredecomp'
    profileregions = regions

    def flredecomp(self, dim=2, size=5, nprocs=2, force=False):
        self.create_mesh(dim, size, force)
        self.create_flml(dim, size)

        self.run_flredecomp(dim, size, nprocs)

    def run_flredecomp(self, dim, size, nprocs):
        infile = self.filename(name='sim', dim=dim, size=size, end='')
        outfile = self.filename(name='sim', dim=dim, size=size, end='_flrd')

        cmd = ['mpiexec', '-n', '%d'%nprocs]
        cmd += [os.environ['FLUIDITY_DIR'] + "/bin/flredecomp"]
        cmd += ['-i', '1', '-o', '%d' % nprocs, '-l', '-v', '-p', infile, outfile]
        try:
            # Execute flredecomp in the generated .flml and mesh files
            subprocess.check_call(cmd)

            # Read performance result from log file
            with file("flredecomp.log-0", "r") as lf:
                log = lf.read()
                self.register_timing("flredecomp", float(re_flredecomp.search(log).group(1)))
                self.register_timing("flredecomp::gmsh_read", float(re_io_gmsh.search(log).group(1)))
                self.register_timing("flredecomp::state", float(re_flrd_state.search(log).group(1)))
                self.register_timing("flredecomp::zoltan", float(re_flrd_zoltan.search(log).group(1)))

        except subprocess.CalledProcessError as e:
            print "Warning: flredecomp failed with size %f" % size

if __name__ == '__main__':
    # Benchmark
    b = FLRedecompMeshing()
    b.main()
