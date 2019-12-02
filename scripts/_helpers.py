import pandas as pd

def configure_logging(snakemake, skip_handlers=False):
    """
    Configure the basic behaviour for the logging module.

    Note: Must only be called once from the __main__ section of a script.

    The setup includes printing log messages to STDERR and to a log file defined
    by either (in priority order): snakemake.log.python, snakemake.log[0] or "logs/{rulename}.log".
    Additional keywords from logging.basicConfig are accepted via the snakemake configuration
    file under snakemake.config.logging.

    Parameters
    ----------
    snakemake : snakemake object
        Your snakemake object containing a snakemake.config and snakemake.log.
    skip_handlers : True | False (default)
        Do (not) skip the default handlers created for redirecting output to STDERR and file.
    """

    import logging

    kwargs = snakemake.config.get('logging', dict())
    kwargs.setdefault("level", "INFO")

    if skip_handlers is False:
        logfile = snakemake.log.get('python', snakemake.log[0] if snakemake.log else f"logs/{snakemake.rule}.log")
        kwargs.update(
            {'handlers': [
                # Prefer the 'python' log, otherwise take the first log for each
                # Snakemake rule
                logging.FileHandler(logfile),
                logging.StreamHandler()
                ]
            })
    logging.basicConfig(**kwargs)

def pdbcast(v, h):
    return pd.DataFrame(v.values.reshape((-1, 1)) * h.values,
                        index=v.index, columns=h.index)

def load_network(fn, tech_costs, config, combine_hydro_ps=True):
    import pypsa
    from add_electricity import update_transmission_costs, load_costs

    opts = config['plotting']

    n = pypsa.Network(fn)

    n.loads["carrier"] = n.loads.bus.map(n.buses.carrier) + " load"
    n.stores["carrier"] = n.stores.bus.map(n.buses.carrier)

    n.links["carrier"] = (n.links.bus0.map(n.buses.carrier) + "-" + n.links.bus1.map(n.buses.carrier))
    n.lines["carrier"] = "AC line"
    n.transformers["carrier"] = "AC transformer"

    n.lines['s_nom'] = n.lines['s_nom_min']
    n.links['p_nom'] = n.links['p_nom_min']

    if combine_hydro_ps:
        n.storage_units.loc[n.storage_units.carrier.isin({'PHS', 'hydro'}), 'carrier'] = 'hydro+PHS'

    # #if the carrier was not set on the heat storage units
    # bus_carrier = n.storage_units.bus.map(n.buses.carrier)
    # n.storage_units.loc[bus_carrier == "heat","carrier"] = "water tanks"

    Nyears = n.snapshot_weightings.sum()/8760.
    costs = load_costs(Nyears, tech_costs, config['costs'], config['electricity'])
    update_transmission_costs(n, costs)

    return n

def aggregate_p_nom(n):
    return pd.concat([
        n.generators.groupby("carrier").p_nom_opt.sum(),
        n.storage_units.groupby("carrier").p_nom_opt.sum(),
        n.links.groupby("carrier").p_nom_opt.sum(),
        n.loads_t.p.groupby(n.loads.carrier,axis=1).sum().mean()
    ])

def aggregate_p(n):
    return pd.concat([
        n.generators_t.p.sum().groupby(n.generators.carrier).sum(),
        n.storage_units_t.p.sum().groupby(n.storage_units.carrier).sum(),
        n.stores_t.p.sum().groupby(n.stores.carrier).sum(),
        -n.loads_t.p.sum().groupby(n.loads.carrier).sum()
    ])

def aggregate_e_nom(n):
    return pd.concat([
        (n.storage_units["p_nom_opt"]*n.storage_units["max_hours"]).groupby(n.storage_units["carrier"]).sum(),
        n.stores["e_nom_opt"].groupby(n.stores.carrier).sum()
    ])

def aggregate_p_curtailed(n):
    return pd.concat([
        ((n.generators_t.p_max_pu.sum().multiply(n.generators.p_nom_opt) - n.generators_t.p.sum())
         .groupby(n.generators.carrier).sum()),
        ((n.storage_units_t.inflow.sum() - n.storage_units_t.p.sum())
         .groupby(n.storage_units.carrier).sum())
    ])

def aggregate_costs(n, flatten=False, opts=None, existing_only=False):
    from six import iterkeys, itervalues

    components = dict(Link=("p_nom", "p0"),
                      Generator=("p_nom", "p"),
                      StorageUnit=("p_nom", "p"),
                      Store=("e_nom", "p"),
                      Line=("s_nom", None),
                      Transformer=("s_nom", None))

    costs = {}
    for c, (p_nom, p_attr) in zip(
        n.iterate_components(iterkeys(components), skip_empty=False),
        itervalues(components)
    ):
        if not existing_only: p_nom += "_opt"
        costs[(c.list_name, 'capital')] = (c.df[p_nom] * c.df.capital_cost).groupby(c.df.carrier).sum()
        if p_attr is not None:
            p = c.pnl[p_attr].sum()
            if c.name == 'StorageUnit':
                p = p.loc[p > 0]
            costs[(c.list_name, 'marginal')] = (p*c.df.marginal_cost).groupby(c.df.carrier).sum()
    costs = pd.concat(costs)

    if flatten:
        assert opts is not None
        conv_techs = opts['conv_techs']

        costs = costs.reset_index(level=0, drop=True)
        costs = costs['capital'].add(
            costs['marginal'].rename({t: t + ' marginal' for t in conv_techs}),
            fill_value=0.
        )

    return costs

def progress_retrieve(url, file):
    import urllib
    from progressbar import ProgressBar

    pbar = ProgressBar(0, 100)

    def dlProgress(count, blockSize, totalSize):
        pbar.update( int(count * blockSize * 100 / totalSize) )

    urllib.request.urlretrieve(url, file, reporthook=dlProgress)


def mocksnakemake(rulename, **wildcards):
    """
    This function is expected to be executed in the 'scripts'-directory within
    the snakemake project. It returns a snakemake.script.Snakemake object,
    based on the Snakefile of the upper directory, such that includes
    mostly all necessary information (input, output, log etc.).

    If a rule has wildcards, you have to specify them in **wildcards.

    Parameters
    ----------
    rulename: str
        name of the rule for which the snakemake object should be generated
    **wildcards:
        keyword arguments fixing the wildcards. Only necessary if wildcards are
        needed.
    """
    import snakemake as sm
    import os
    import logging
    from pypsa.descriptors import Dict
    from os.path import abspath

    os.chdir('..')
    for p in sm.SNAKEFILE_CHOICES:
        if os.path.exists(p):
            snakefile = p
            break
    workflow = sm.Workflow(snakefile)
    workflow.include(snakefile)
    rule = workflow.get_rule(rulename)
    wc = Dict(wildcards)

    # make the input files accessable by taking the absolut paths
    def make_io_accessable(smfiles):
        if not smfiles:
            return
        # for mildy hacky input functions (like make_summary):
        if len(smfiles) == 1 and callable(smfiles[0]):
            new_input_files = smfiles[0](wc)
            # overwrite smfiles with extracted files from function
            smfiles = sm.io.InputFiles()
            for index, p in enumerate(new_input_files):
                smfiles.insert(index, p)
        # now iterate over each item and make path an absolut path
        files = sm.io.InputFiles()
        for index, (key, p) in enumerate(smfiles.allitems()):
            # case that item is a function
            if callable(p):
                p = p(wc)
            if isinstance(p, str):
                files.insert(index, sm.io.apply_wildcards(abspath(p), wc))
            else:
                files.insert(index, p)
            if key is not None:
                files.add_name(key)
        return files

    Input = make_io_accessable(rule.input)
    Output = make_io_accessable(rule.output)
    if not rule.log:
        rule.log.insert(0, f"logs/{rule.name}.log")
    Log = make_io_accessable(rule.log)
    # create log dir if not existent
    for file in list(Log) + list(Output):
        dir = os.path.dirname(file)
        if not os.path.exists(dir):
            logging.info(f'Log directory {dir} not existent, creating it.')
            os.mkdir(dir)
#    # create output dir if not existent
#    for outfile in Output:
#        dir = os.path.dirname(outfile)
#        if not os.path.exists(dir):
#            logging.info(f'Log directory {dir} not existent, creating it.')
#            os.mkdir(dir)

    snakemake = sm.script.Snakemake(input=Input, output=Output,
                            params=rule.params, wildcards=wc, threads=None,
                            resources=rule.resources, log=Log,
                            config=workflow.config, rulename=rule.name,
                            bench_iteration=None)

    os.chdir(old_wd)
    return snakemake
