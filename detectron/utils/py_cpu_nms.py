# --------------------------------------------------------
# Fast R-CNN
# Copyright (c) 2015 Microsoft
# Licensed under The MIT License [see LICENSE for details]
# Written by Ross Girshick
# --------------------------------------------------------

import numpy as np
from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
from IPython import embed
from detectron.core.config import cfg
debug = False

def soft(dets, confidence=None, ax = None):
    thresh = cfg.STD_TH #.6
    score_thresh = .7
    sigma = .5 
    N = len(dets)
    x1 = dets[:, 0].copy()
    y1 = dets[:, 1].copy()
    x2 = dets[:, 2].copy()
    y2 = dets[:, 3].copy()
    scores = dets[:, 4].copy()
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    ious = np.zeros((N,N))
    kls = np.zeros((N,N))
    for i in range(N):
        xx1 = np.maximum(x1[i], x1)
        yy1 = np.maximum(y1[i], y1)
        xx2 = np.minimum(x2[i], x2)
        yy2 = np.minimum(y2[i], y2)

        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        ovr = inter / (areas[i] + areas - inter)
        ious[i,:] = ovr
        kl = np.zeros_like(ovr)
        for j in range(4):
            std1 = confidence[i, j]
            stdo = confidence[:, j]
            mean1 = dets[i, j]
            meano = dets[:, j]
            kl += np.log(stdo/std1) + (std1**2 + (mean1 - meano)**2) / 2 / (stdo**2) - .5
        kls[i, :] = kl.copy()
    if False and len(kls) != 0:
        print("std",kls.std())
        print("mean",kls.mean())
        print("max",kls.max())
        print("min",kls.min())


             
    i = 0
    while i < N:
        maxpos = dets[i:N, 4].argmax()
        maxpos += i
        dets[[maxpos,i]] = dets[[i,maxpos]]
        areas[[maxpos,i]] = areas[[i,maxpos]]
        confidence[[maxpos,i]] = confidence[[i,maxpos]]
        scores[[maxpos,i]] = scores[[i,maxpos]]
        ious[[maxpos,i]] = ious[[i,maxpos]]
        ious[:,[maxpos,i]] = ious[:,[i,maxpos]]
        kls[[maxpos,i]] = kls[[i,maxpos]]
        kls[:,[maxpos,i]] = kls[:,[i,maxpos]]

        #                               N                           N & (scores[(i+1):N] > score_thresh)
        #ovr_bbox = np.where((kls[i, (i+1):N] < 300) & (scores[(i+1):N] > score_thresh))[0] + i + 1
        #ovr_bbox = np.where((ious[i, (i+1):N] > thresh))[0] + i + 1
        #ovr_bbox = np.hstack(([i], ovr_bbox))
        ovr_bbox = np.where((ious[i, :N] > thresh))[0]
        avg_bbox = (dets[ovr_bbox, :4] * scores[ovr_bbox, np.newaxis]).sum(0) / scores[ovr_bbox].sum()
        avg_std_bbox = (dets[ovr_bbox, :4] / confidence[ovr_bbox]).sum(0) / (1/confidence[ovr_bbox]).sum(0)
        avg_stds_bbox = (dets[ovr_bbox, :4] / confidence[ovr_bbox]**2).sum(0) / (1/confidence[ovr_bbox]**2).sum(0)
        mean_bbox = dets[ovr_bbox, :4].mean(0)
        tx1, ty1, tx2, ty2 = dets[i, :4].copy()
        #dets[i,:4] = avg_bbox
        if cfg.STD_NMS:
            #dets[i,:4] = avg_bbox
            dets[i,:4] = avg_std_bbox
            #dets[i,:4] = mean_bbox
            pass
        else:
            assert(False)
        #dets[i,:4] = avg_stds_bbox
        #dets[i,:4] = mean_bbox

        areai = areas[i] #(tx2 - tx1 + 1) * (ty2 - ty1 + 1)
        pos = i + 1
        while pos < N:
            if ious[i , pos] > 0:
                ovr =  ious[i , pos]#float(inter) / (areai + area - inter)
                dets[pos, 4] *= np.exp(-(ovr * ovr)/sigma)
                if dets[pos, 4] < 0.001:
                    dets[[pos, N-1]] = dets[[N-1, pos]]
                    areas[[pos, N-1]] = areas[[N-1, pos]]
                    scores[[pos, N-1]] = scores[[N-1, pos]]
                    confidence[[pos, N-1]] = confidence[[N-1, pos]]
                    ious[[pos, N-1]] = ious[[N-1, pos]]
                    ious[:,[pos, N-1]] = ious[:,[N-1, pos]]
                    kls[[pos, N-1]] = kls[[N-1, pos]]
                    kls[:,[pos, N-1]] = kls[:,[N-1, pos]]
                    N -= 1
                    pos -= 1
            pos += 1
        i += 1
    keep=[i for i in range(N)]
    return dets[keep], keep

def greedy(dets, thresh=None, confidence=None, ax = None):
    x1 = dets[:, 0]
    y1 = dets[:, 1]
    x2 = dets[:, 2]
    y2 = dets[:, 3]
    scores = dets[:, 4]
    if len(scores) == 0:
        return []
    elif len(scores) == 1:
        return [0]

    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    ious = np.zeros([len(x1), len(x1)])
    w2 = .42
    for i in range(len(x1)):
        xx1 = np.maximum(x1[i], x1)
        yy1 = np.maximum(y1[i], y1)
        xx2 = np.minimum(x2[i], x2)
        yy2 = np.minimum(y2[i], y2)

        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        ovr = inter / (areas[i] + areas - inter)
        for j in range(len(ovr)):
            if i == j:
                ious[i, i] = -(1-w2) * scores[i]
                ious[i,j] += w2 * ovr[j]
            else:
                ious[i,j] = w2 * ovr[j]
    score = 0
    keep = []
    remain = list(range(len(x2)))
    while len(remain) > 0:
        if len(keep) == 0:
            inc = np.diag(ious)[remain]
        else:
            try:
                d = ious[remain][:, keep]
                if len(d.shape) == 2:
                    d = d.sum(1)
                inc = d+np.diag(ious)[remain]
            except:
                embed()
        if inc.min() >= 0:
            break
        idx = inc.argmin()
        obj = remain[idx]
        remain.remove(obj)
        keep.append(obj)
    if len(keep) !=0:
        print(len(keep), len(x1))

    return keep

def qb(dets, thresh=None, confidence=None, ax = None):
    from dwave_qbsolv import QBSolv
    x1 = dets[:, 0]
    y1 = dets[:, 1]
    x2 = dets[:, 2]
    y2 = dets[:, 3]
    scores = dets[:, 4]
    if len(scores) == 0:
        return []
    elif len(scores) == 1:
        return [0]

    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    ious = {}#np.zeros([len(x1), len(x1)])
    w2 = 0.4
    for i in range(len(x1)):
        xx1 = np.maximum(x1[i], x1)
        yy1 = np.maximum(y1[i], y1)
        xx2 = np.minimum(x2[i], x2)
        yy2 = np.minimum(y2[i], y2)

        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        ovr = inter / (areas[i] + areas - inter)
        for j in range(len(ovr)):
            if i == j:
                ious[i, i] = -(1-w2) * scores[i]
                ious[i,j] += w2 * ovr[j]
            else:
                ious[i,j] = w2 * ovr[j]
    response = QBSolv().sample_qubo(ious, verbosity=0)
    samples = list(response.samples())[0]
    keep = []
    for i in range(len(x1)):
        if samples[i] == 1:
            keep.append(i)
    #if len(keep) == 0:
    #    keep_dets = np.ndarray((0, 4))
    #else:
    #    keep_dets = dets[keep]
    ## print(keep_dets)
    #return keep_dets
    return keep



def py_cpu_nms(dets, thresh):
    """Pure Python NMS baseline."""
    x1 = dets[:, 0]
    y1 = dets[:, 1]
    x2 = dets[:, 2]
    y2 = dets[:, 3]
    scores = dets[:, 4]

    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        ovr = inter / (areas[i] + areas[order[1:]] - inter)

        inds = np.where(ovr <= thresh)[0]
        order = order[inds + 1]

    return keep

def show_box(ax, bbox, text, color):
    ax.add_patch(
        Rectangle((bbox[0], bbox[1]),
                    bbox[2] - bbox[0],
                    bbox[3] - bbox[1], fill=False,
                    edgecolor=color, linewidth=3)
        )       
    ax.text(bbox[0] + 3, bbox[1]+7,
        text,
        fontsize=7, color=color)

def confidence_nms(dets, thresh, confidence, ax = None):
    softnms = 0
    softthresh = .4
    score_thresh = .7
    keep_dets = []
    x1 = dets[:, 0]
    y1 = dets[:, 1]
    x2 = dets[:, 2]
    y2 = dets[:, 3]
    scores = dets[:, 4]

    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        ovr = inter / (areas[i] + areas[order[1:]] - inter)

        ovr_bbox = order[np.where((ovr > thresh) & (scores[order[1:]] > score_thresh))[0] + 1]
        ovr_bbox = np.hstack(([i], ovr_bbox))
        avg_std_bbox = (dets[ovr_bbox, :4] / confidence[ovr_bbox]).sum(0) / (1/confidence[ovr_bbox]).sum(0)
        avg_bbox = (dets[ovr_bbox, :4] * scores[ovr_bbox, np.newaxis]).sum(0) / scores[ovr_bbox].sum()
        merged = (dets[ovr_bbox, :4] / (confidence[ovr_bbox] * (1/confidence[ovr_bbox]).sum(0))).sum(0) 
        bbox = dets[ovr_bbox, :4][(confidence[ovr_bbox].sum(1)).argmin(), :]

        lrdu = confidence[ovr_bbox].argmin(0)
        split_box = np.zeros_like(bbox)
        for i in range(4):
            split_box[i] = dets[ovr_bbox, :4][lrdu[i]][i]
        min_bbox = dets[ovr_bbox, :4][lrdu, range(4)]


        # keep_dets.append(merged)
        #keep_dets.append(avg_bbox)
        keep_dets.append(avg_std_bbox)
        #keep_dets.append(min_bbox)
        # keep_dets.append(bbox)
        # keep_dets.append(split_box)
        # keep_dets.append(dets[i])
        if ax is None:
            pass
        else:
            if scores[i] > score_thresh:
                # print(dets[ovr_bbox, :4].shape, confidence[ovr_bbox].shape)
                # bbox = dets[ovr_bbox, :4][((1/confidence[ovr_bbox]).sum(1)).argmax(), :]
                ax.add_patch(
                    Rectangle((bbox[0], bbox[1]),
                                bbox[2] - bbox[0],
                                bbox[3] - bbox[1], fill=False,
                                edgecolor='blue', linewidth=3)
                    )       
                ax.text(bbox[0] + 3, bbox[1]+7,
                    'b',# bbox=dict(facecolor='blue', alpha=0.5),
                    fontsize=7, color='white')

                # lrdu = confidence[ovr_bbox].argmin(0)
                # bbox[0] = x1[lrdu[0]]
                # bbox[1] = y1[lrdu[1]]
                # bbox[2] = x2[lrdu[2]]
                # bbox[3] = y2[lrdu[3]]
                # ax.add_patch(
                #     Rectangle((bbox[0], bbox[1]),
                #                 bbox[2] - bbox[0],
                #                 bbox[3] - bbox[1], fill=False,
                #                 edgecolor='green', linewidth=3)
                #     )    

                ax.add_patch(
                    Rectangle((merged[0], merged[1]),
                                merged[2] - merged[0],
                                merged[3] - merged[1], fill=False,
                                edgecolor='green', linewidth=3)
                    )   
                ax.add_patch(
                    Rectangle((dets[i][0], dets[i][1]),
                                dets[i][2] - dets[i][0],
                                dets[i][3] - dets[i][1], fill=False,
                                edgecolor='red', linewidth=3)
                    )       

        inds = np.where(ovr <= thresh)[0]
        order = order[inds + 1]
 
    
    if debug:
        print((np.array(keep_dets), scores[keep, np.newaxis]))
    if len(keep) == 0:
        keep_dets = np.ndarray((0, 4))
    else:
        keep_dets = np.hstack((np.array(keep_dets), scores[keep, np.newaxis]))
    # print(keep_dets)
    return keep_dets

def avg_nms(dets, thresh):
    pass
