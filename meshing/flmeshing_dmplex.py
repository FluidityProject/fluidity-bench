from flmeshing import FLMeshing
import re

fluidity_regexes = {'fluidity' : re.compile(r"\/fluidity\s+::\s+([0-9\.]+)"),
                    'fluidity::state' : re.compile(r"I\/O\s+::\s+Populate\_State\s+::\s+([0-9\.]+)"),
                    'dmplex': re.compile(r"I\/O\s+::\s+DMPlex\s+::\s+([0-9\.]+)"),
                    'dmplex::create': re.compile(r"I\/O\s+::\s+DMPlex\s+::\s+Create\s+::\s+([0-9\.]+)"),
                    'dmplex::distribute': re.compile(r"I\/O\s+::\s+DMPlex\s+::\s+Distribute\s+::\s+([0-9\.]+)"),
                    }

class FLDMPlexMeshing(FLMeshing):
    benchmark = 'fldmplex'
    description = 'Fluidity DMPlex benchmark'

    method = 'fldmplex'
    profileregions = fluidity_regexes.keys()

    def __init__(self, **kwargs):
        super(FLDMPlexMeshing, self).__init__(**kwargs)
        args, _ = self.parser().parse_known_args()
        self._force = args.force

    def fldmplex(self, dim=2, size=5, nprocs=2, timesteps=1, ascii=False):
        self.create_mesh(dim, size, self._force)
        self.create_flml(dim, size, timesteps=timesteps)

        # Then run Fluidity to benchmark initial setup
        flmlfile = self.filename(name='sim', dim=dim, size=size, end='.flml')
        args = ['-l', '-p', flmlfile]
        self.run_application(nprocs, 'fluidity', args, logfile='fluidity.log-0', regexes=fluidity_regexes)


if __name__ == '__main__':
    # Benchmark
    b = FLDMPlexMeshing()
    b.main()
