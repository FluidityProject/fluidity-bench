from flmeshing import FLMeshing
import os
import subprocess

regions = ['flredecomp']

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
        except subprocess.CalledProcessError as e:
            print "Warning: flredecomp failed with size %f" % size

if __name__ == '__main__':
    # Benchmark
    b = FLRedecompMeshing()
    b.main()
