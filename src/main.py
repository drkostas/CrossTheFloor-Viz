#!/usr/bin/env python
import logging
from logging.handlers import TimedRotatingFileHandler
from logging import StreamHandler
import argparse
import traceback
from typing import *
import pandas as pd
import numpy as np
import re

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 20)
pd.set_option('display.width', 1000)

from configuration.configuration import Configuration
from crawler.crawler import AbstractCrawler
from visualizer.visualizer import AbstractVisualizer
from crawler.parliament_members_crawler import ParliamentMembersCrawler
from visualizer.plotly_visualizer import PlotlyVisualizer
from pandas_manager.pandas_manager import PandasManager

logger = logging.getLogger('MAIN')


def __setup_log__(log_path: str, debug=False) -> None:
    from os import sep
    if log_path is None:
        raise Exception('No log path was provided!')

    log_path = log_path.split(sep)
    if len(log_path) > 1:
        from os import makedirs
        try:
            makedirs((sep.join(log_path[:-1])))
        except FileExistsError:
            pass
    log_filename = sep.join(log_path)
    time_rotating_handler = TimedRotatingFileHandler(log_filename, when='midnight', interval=1)
    stream_handler = StreamHandler()
    logging.basicConfig(level=logging.INFO if debug is not True else logging.DEBUG,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S'
                        )
    logger.addHandler(time_rotating_handler)
    logger.addHandler(stream_handler)


def __bootstrap__() -> argparse.Namespace:
    import argparse

    parser = argparse.ArgumentParser(description='Create a Sankey Diagram by providing a configuration file',
                                     add_help=False)
    required_arguments = parser.add_argument_group('Required Arguments')
    config_file_params = {
        'type': argparse.FileType('r'),
        'required': True,
        'help': "The configuration file"
    }
    required_arguments.add_argument('-c', '--config-file', **config_file_params)
    required_arguments.add_argument('-l', '--log-file', help="Location to store log file")

    optional = parser.add_argument_group('Optional Arguments')
    optional.add_argument("-h", "--help", action="help", help="show this help message and exit")
    optional.add_argument('-d', '--debug', action='store_true', help='enables the debug log messages')
    optional.add_argument('-p', '--plot-name', help="The name of the Sankey Diagram plot")
    return parser.parse_args()


def __setup_classes__(args: argparse.Namespace) -> Tuple[AbstractCrawler, AbstractVisualizer, str]:
    config = Configuration(args.config_file)
    if config.get_source_type() == 'ParliamentMembersCrawler':
        crawler = ParliamentMembersCrawler(config=config.get_source())
    else:
        raise Exception('Unknown source type!')
    if config.get_target_type() == 'plotly':
        visualizer = PlotlyVisualizer(config=config.get_target())
    else:
        raise Exception('Unknown source type!')

    return crawler, visualizer, config.get_plot_name()


def main():
    args = __bootstrap__()
    log_fn = args.log_file
    __setup_log__(log_fn, args.debug)
    crawler, visualizer, plot_name = __setup_classes__(args)

    df_generator = crawler.get_tables()
    pandas_manager = PandasManager(df_generator=df_generator)
    merged_df, plot_cols, name_col = pandas_manager.df_from_generator()
    nodes_df = pandas_manager.create_nodes_df(merged_df, plot_cols)
    edges_df = pandas_manager.create_edges_df(merged_df, plot_cols, name_col)

    print(nodes_df)
    print(edges_df)

    # visualizer.create_sankey_diagram(data_df=merged_df,
    #                                  attribute_cols=plot_cols,
    #                                  name_col=name_col,
    #                                  plot_name=plot_name)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.error(str(e))
        logging.error(str(traceback.format_exc()))
        raise e
