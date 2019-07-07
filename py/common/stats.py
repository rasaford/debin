from elements.function import Function
from elements.offsets import Offset, GivOffset, DirectOffset
from elements.offsets import StringArrayOffset, IndirectOffset, TempOffset
from elements.regs import RegBase, GivReg, Reg
from elements.givs import GivElm, IntConst, StringConst
from elements.givs import Flag, Insn, CodeOffset, VirtualElm
from elements.givs import SwitchTable, NodeType, OpNode, OtherVarNode
from elements.ttype import Ttype
from depgraph.nodes import INF_NODES
from common.constants import UNKNOWN_LABEL
from common.timer import TIMER
import json


class Stats:
    def __init__(self, binary):
        self.binary = binary
        self.corrects = dict()
        self.errors = dict()
        self.stated = False

    def stat(self):
        if not self.stated:
            self.stated = True

            self.binary.nodes.stat()
            self.binary.edges.stat()

            self.name_known = Function.known + Offset.known + Reg.known
            self.name_unknown = Function.unknown + Offset.unknown + Reg.unknown
            self.name_inf = Function.inf + Offset.inf + Reg.inf
            self.name_correct = Function.correct + Offset.correct + RegBase.correct

            self.known = self.name_known + Ttype.known
            self.unknown = self.name_unknown + Ttype.unknown
            self.inf = self.name_inf + Ttype.inf
            self.giv = Function.giv + Reg.giv + Offset.giv + GivElm.total
            self.total = self.name_inf + Ttype.inf + self.giv
            self.tp_1p = Offset.tp_1p + RegBase.tp_1p
            self.fp_1p = Offset.fp_1p + RegBase.fp_1p
            self.tn_1p = Offset.tn_1p + RegBase.tn_1p
            self.fn_1p = Offset.fn_1p + RegBase.fn_1p
            self.correct = self.name_correct + Ttype.correct

    def stat_result(self, nodes_json):
        for node_json in nodes_json:
            if 'inf' in node_json and node_json['inf'] != UNKNOWN_LABEL:
                node = self.binary.nodes.nodes[node_json['v']]
                train_name = node.train_name
                test_name = node_json['inf']
                if train_name == test_name:
                    if type(node) is IndirectOffset:
                        IndirectOffset.correct += 1
                        Offset.correct += 1
                    elif type(node) is DirectOffset:
                        DirectOffset.correct += 1
                        Offset.correct += 1
                    elif type(node) is StringArrayOffset:
                        StringArrayOffset.correct += 1
                        DirectOffset.correct += 1
                        Offset.correct += 1
                    elif type(node) is Reg:
                        Reg.correct += 1
                        RegBase.correct += 1
                    elif type(node) is Function:
                        Function.correct += 1
                    elif type(node) is Ttype:
                        Ttype.correct += 1
                        type(node.owner).ttype_correct += 1
                        if isinstance(node.owner, StringArrayOffset):
                            DirectOffset.ttype_correct += 1

        for node in self.binary.nodes.nodes.values():
            if type(node) in INF_NODES \
                    and not (isinstance(node, Function) and node.is_name_given) \
                    and not (isinstance(node, DirectOffset) and node.is_name_given):
                if node.train_name == node.test_name:
                    if (node.train_name, node.test_name) not in self.corrects:
                        self.corrects[(node.train_name, node.test_name)] = 0
                    self.corrects[(node.train_name, node.test_name)] += 1
                else:
                    if (node.train_name, node.test_name) not in self.errors:
                        self.errors[(node.train_name, node.test_name)] = 0
                    self.errors[(node.train_name, node.test_name)] += 1

    def dump_corrects(self):
        corrects = sorted(self.corrects.items(), key=lambda i: i[1], reverse=True)
        with open(self.binary.config.CORRECTS_PATH, 'w') as w:
            for c in corrects:
                w.write('\t{} : {} -> {}\n'.format(c[1], c[0][0], c[0][1]))

    def dump_errors(self):
        errors = sorted(self.errors.items(), key=lambda i: i[1], reverse=True)
        with open(self.binary.config.ERRORS_PATH, 'w') as w:
            for e in errors:
                w.write('\t{} : {} -> {}\n'.format(e[1], e[0][0], e[0][1]))

    def dump(self):
        with open(self.binary.config.STAT_PATH, 'w') as w:
            stats = {}
            stats['path'] = self.binary.config.BINARY_PATH

            denominator = self.tp_1p + self.fp_1p
            precision_1p = self.tp_1p / denominator if denominator != 0 else 0
            denominator = self.tp_1p + self.fn_1p
            recall_1p = self.tp_1p / denominator if denominator != 0 else 0
            denominator = precision_1p + recall_1p
            f1_1p = 2 * precision_1p * recall_1p / denominator if denominator != 0 else 0
            denominator = self.tp_1p + self.fp_1p + self.tn_1p + self.fn_1p
            accuracy_1p = (self.tp_1p + self.tn_1p) / denominator if denominator != 0 else 0

            stats['precision_1p'] = precision_1p
            stats['recall_1p'] = recall_1p
            stats['f1_1p'] = f1_1p
            stats['accuracy_1p'] = accuracy_1p

            precision_2p = self.correct / self.inf if self.inf != 0 else 0
            recall_2p = self.correct / self.known if self.known != 0 else 0
            denominator = recall_2p + precision_2p
            f1_2p = 2 * recall_2p * precision_2p / denominator if denominator != 0 else 0

            stats['precision_2p'] = precision_2p
            stats['recall_2p'] = recall_2p
            stats['f1_2p'] = f1_2p

            precision_name_2p = self.name_correct / self.name_inf if self.name_inf != 0 else 0
            recall_name_2p = self.name_correct / self.name_known if self.name_known != 0 else 0
            denominator = recall_name_2p + precision_name_2p
            f1_name_2p = 2 * recall_name_2p * precision_name_2p / denominator if denominator != 0 else 0

            stats['precision_name_2p'] = precision_name_2p
            stats['recall_name_2p'] = recall_name_2p
            stats['f1_name_2p'] = f1_name_2p

            precision_ttype_2p = Ttype.correct / Ttype.inf if Ttype.inf != 0 else 0
            recall_ttype_2p = Ttype.correct / Ttype.known if Ttype.known != 0 else 0
            denominator = recall_ttype_2p + precision_ttype_2p
            f1_ttype_2p = 2 * recall_ttype_2p * precision_ttype_2p / denominator if denominator != 0 else 0

            stats['precision_ttype_2p'] = precision_ttype_2p
            stats['recall_ttype_2p'] = recall_ttype_2p
            stats['f1_ttype_2p'] = f1_ttype_2p


            stats['time'] = str(TIMER)


            stats['total'] = self.total
            stats['known'] = self.known
            stats['unknown'] = self.unknown
            stats['inf'] = self.inf
            stats['correct'] = self.correct

            stats['name_known'] = self.name_known
            stats['name_unknown'] = self.name_unknown
            stats['name_inf'] = self.name_inf
            stats['name_correct'] = self.name_correct

            stats['ttype_known'] = Ttype.known
            stats['ttype_unknown'] = Ttype.unknown
            stats['ttype_inf'] = Ttype.inf
            stats['ttype_correct'] = Ttype.correct

            stats['function_total'] = Function.total
            stats['function_known'] = Function.known
            stats['function_unknown'] = Function.unknown
            stats['function_inf'] = Function.inf
            stats['function_correct'] = Function.correct

            stats['reg_total'] = Reg.total
            stats['reg_known'] = Reg.known
            stats['reg_unknown'] = Reg.unknown
            stats['reg_inf'] = Reg.inf
            stats['reg_tp_1p'] = RegBase.tp_1p
            stats['reg_fp_1p'] = RegBase.fp_1p
            stats['reg_tn_1p'] = RegBase.tn_1p
            stats['reg_fn_1p'] = RegBase.fp_1p
            stats['reg_correct'] = Reg.correct

            stats['offset_total'] = Offset.total
            stats['offset_known'] = Offset.known
            stats['offset_unknown'] = Offset.unknown
            stats['offset_inf'] = Offset.inf
            stats['offset_correct'] = Offset.correct

            stats['indirectoffset_total'] = IndirectOffset.total
            stats['indirectoffset_known'] = IndirectOffset.known
            stats['indirectoffset_unknown'] = IndirectOffset.unknown
            stats['indirectoffset_inf'] = IndirectOffset.inf
            stats['indirectoffset_tp_1p'] = IndirectOffset.tp_1p
            stats['indirectoffset_fp_1p'] = IndirectOffset.fp_1p
            stats['indirectoffset_tn_1p'] = IndirectOffset.tn_1p
            stats['indirectoffset_fn_1p'] = IndirectOffset.fp_1p
            stats['indirectoffset_correct'] = IndirectOffset.correct

            stats['directoffset_total'] = DirectOffset.total
            stats['directoffset_known'] = DirectOffset.known
            stats['directoffset_unknown'] = DirectOffset.unknown
            stats['directoffset_inf'] = DirectOffset.inf
            stats['directoffset_correct'] = DirectOffset.correct

            stats['function_ttype_total'] = Function.ttype_total
            stats['function_ttype_known'] = Function.ttype_known
            stats['function_ttype_unknown'] = Function.ttype_unknown
            stats['function_ttype_inf'] = Function.ttype_inf
            stats['function_ttype_correct'] = Function.ttype_correct

            stats['reg_ttype_total'] = Reg.ttype_total
            stats['reg_ttype_known'] = Reg.ttype_known
            stats['reg_ttype_unknown'] = Reg.ttype_unknown
            stats['reg_ttype_inf'] = Reg.ttype_inf
            stats['reg_ttype_correct'] = Reg.ttype_correct

            stats['indirectoffset_ttype_total'] = IndirectOffset.ttype_total
            stats['indirectoffset_ttype_known'] = IndirectOffset.ttype_known
            stats['indirectoffset_ttype_unknown'] = IndirectOffset.ttype_unknown
            stats['indirectoffset_ttype_inf'] = IndirectOffset.ttype_inf
            stats['indirectoffset_ttype_correct'] = IndirectOffset.ttype_correct
            
            stats['directoffset_ttype_total'] = DirectOffset.ttype_total
            stats['directoffset_ttype_known'] = DirectOffset.ttype_known
            stats['directoffset_ttype_unknown'] = DirectOffset.ttype_unknown
            stats['directoffset_ttype_inf'] = DirectOffset.ttype_inf
            stats['directoffset_ttype_correct'] = DirectOffset.ttype_correct

            json.dump(stats, w)
