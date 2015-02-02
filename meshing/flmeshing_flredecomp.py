from flmeshing import FLMeshing

regions = ['flredecomp']

class FLRedecompMeshing(FLMeshing):
    benchmark = 'flredecomp'
    description = 'Fluidity flredecomp benchmark'

    method = 'flredecomp'
    profileregions = regions

    def flredecomp(self, dim=2, size=5, force=False):
        self.create_mesh(dim, size, force)

if __name__ == '__main__':
    # Benchmark
    b = FLRedecompMeshing()
    b.main()
