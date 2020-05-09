#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Desc    : dynamic plot alc metric

from sklearn.metrics import auc
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from autodl.utils.plot_base_metric import PlotBaseMetric
from autodl.utils.util import transform_time
from autodl.utils.logger import logger
from autodl.auto_scoring.score import auc_step


class PlotAlc(PlotBaseMetric):

    def __init__(self, method="step", transform=None, task_name=None, area_color="cyan", fill_area=True,
                 model_name=None, clear_figure=True, show_final_score=True, show_title=True, **kwargs):
        """
        Args:
            method: string, can be one of ['step', 'trapez']
            transform: callable that transform [0, time_budget] into [0, 1]. If `None`,
                use the default transformation
                lambda t: np.log2(1 + t / time_budget)
            task_name: string, name of the task
            area_color: matplotlib color, color of the area under learning curve
            fill_area: boolean, fill the area under the curve or not
            model_name: string, name of the model (learning algorithm).
            clear_figure: boolean, clear previous figures or not
            fig: the figure to plot on
            show_final_score: boolean, show the last score or not
            show_title: boolean, show the plot title or not
            **kwargs:
        """
        # figure configuration
        self.method = method
        self.transform = transform
        self.task_name = task_name
        self.area_color = area_color
        self.fill_area = fill_area
        self.model_name = model_name
        self.clear_figure = clear_figure
        self.fig = None
        self.show_final_score = show_final_score
        self.show_title = show_title
        self.kwargs = kwargs

        self.cur_frame = 0
        self.fig = None
        self.ax = None

        self.init_plot()

    def init_plot(self):
        self.fig, self.ax = plt.subplots()

    def check_conditions(self, timestamps, scores, start_time):
        le = len(timestamps)
        if not le == len(scores):
            raise ValueError("The number of timestamps {} ".format(le) +
                             "should be equal to the number of " +
                             "scores {}!".format(len(scores)))
        for i in range(le):
            if i < le - 1 and not timestamps[i] <= timestamps[i + 1]:
                raise ValueError("The timestamps should be increasing! But got " +
                                 "[{}, {}] ".format(timestamps[i], timestamps[i + 1]) +
                                 "at index [{}, {}].".format(i, i + 1))
            if timestamps[i] < start_time:
                raise ValueError("The timestamp {} at index {}".format(timestamps[i], i) +
                                 " is earlier than start time {}!".format(start_time))

    def plot_learning_curve(self, timestamps, scores,
                            start_time=0, time_budget=7200):
        """Plot learning curve using scores and corresponding timestamps.

        Args:
          timestamps: iterable of float, each element is the timestamp of
            corresponding performance. These timestamps should be INCREASING.
          scores: iterable of float, scores at each timestamp
          start_time: float, the start time, should be smaller than any timestamp
          time_budget: float, the time budget, should be larger than any timestamp
          transform: callable that transform [0, time_budget] into [0, 1]. If `None`,
            use the default transformation
                lambda t: np.log2(1 + t / time_budget)
        Returns:
          alc: float, the area under learning curve.
          fig: the figure with learning curve
        Raises:
          ValueError: if the length of `timestamps` and `scores` are not equal,
            or if `timestamps` is not increasing, or if certain timestamp is not in
            the interval [start_time, start_time + time_budget], or if `method` has
            bad values.
        """
        le = len(timestamps)

        self.check_conditions(timestamps, scores, start_time)

        timestamps = [t for t in timestamps if t <= time_budget + start_time]
        if len(timestamps) < le:
            logger.warning("Some predictions are made after the time budget! " +
                           "Ignoring all predictions from the index {}.".format(len(timestamps)))
            scores = scores[:len(timestamps)]
        if self.transform is None:
            t0 = 60
            # default transformation
            transform = lambda t: transform_time(t, time_budget, t0=t0)
            xlabel = "Transformed time: " + \
                     r'$\tilde{t} = \frac{\log (1 + t / t_0)}{ \log (1 + T / t_0)}$ ' + \
                     ' ($T = ' + str(int(time_budget)) + '$, ' + \
                     ' $t_0 = ' + str(int(t0)) + '$)'
        else:
            xlabel = "Transformed time: " + r"$\tilde{t}$"

        # call init_plot when self.cur_frame = 0

        relative_timestamps = [t - start_time for t in timestamps]
        # Transform X
        X = [transform(t) for t in relative_timestamps]
        Y = list(scores.copy())
        # Add origin as the first point of the curve
        X.insert(0, 0)
        Y.insert(0, 0)
        # Draw learning curve
        if self.clear_figure:
            plt.clf()
        if self.fig is None or len(self.fig.axes) == 0:
            fig = plt.figure(figsize=(7, 7.07))
            ax = fig.add_subplot(111)
            if self.show_title:
                plt.title("Learning curve for task: {}".format(self.task_name), y=1.06)
            ax.set_xlabel(xlabel)
            ax.set_xlim(left=0, right=1)
            ax.set_ylabel("score (2 * AUC - 1)")
            ax.set_ylim(bottom=-0.01, top=1)
            ax.grid(True, zorder=5)
            # Show real time in seconds in a second x-axis
            ax2 = ax.twiny()
            ticks = [10, 60, 300, 600, 1200] + list(range(1800, int(time_budget) + 1, 1800))
            ax2.set_xticks([transform(t) for t in ticks])
            ax2.set_xticklabels(ticks)
        ax = fig.axes[0]
        if self.method == "step":
            drawstyle = "steps-post"
            step = "post"
            auc_func = auc_step
        elif self.method == "trapez":
            drawstyle = "default"
            step = None
            auc_func = auc
        else:
            raise ValueError("The `method` variable should be one of " +
                             "['step', 'trapez']!")
        # Add a point on the final line using last prediction
        X.append(1)
        Y.append(Y[-1])
        # Compute AUC using step function rule or trapezoidal rule
        alc = auc_func(X, Y)
        if self.model_name:
            label = "{}: ALC={:.4f}".format(self.model_name, alc)
        else:
            label = "ALC={:.4f}".format(alc)
        # Plot the major part of the figure: the curve
        if "marker" not in self.kwargs:
            self.kwargs["marker"] = "o"
        if "markersize" not in self.kwargs:
            self.kwargs["markersize"] = 3
        if "label" not in self.kwargs:
            self.kwargs["label"] = label
        ax.plot(X[:-1], Y[:-1], drawstyle=drawstyle, **self.kwargs)
        # Fill area under the curve
        if self.fill_area:
            ax.fill_between(X, Y, color=self.area_color, step=step)
        # Show the latest/final score
        if self.show_final_score:
            ax.text(X[-1], Y[-1], "{:.4f}".format(Y[-1]))
        # Draw a dotted line from last prediction
        self.kwargs["linestyle"] = "--"
        self.kwargs["linewidth"] = 1
        self.kwargs["marker"] = None
        self.kwargs.pop("label", None)
        ax.plot(X[-2:], Y[-2:], **self.kwargs)
        ax.legend()
        return alc, fig
