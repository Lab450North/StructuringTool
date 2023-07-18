import os
import sys
import numpy as np
import re

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


class SPCFUtils:
    @staticmethod
    def leadZeroCleanEnd(targetDfLen, x):
        res = np.concatenate([np.array([0]), x])
        lenDiff = targetDfLen - len(res)
        if lenDiff < 0:
            # print("******ECHO******")
            return res[:targetDfLen]
        elif lenDiff > 0:
            return np.pad(res, (0, lenDiff), 'edge')
        else:
            return res
        
    
    @staticmethod
    def convertToDict(**kwargs):
        return kwargs


    @staticmethod
    def rampSchdule(ramp, pxSchedule = "100"):
        rampNotional = SPCFUtils.convertIntexRamp(ramp, term = None, divisor=1.0/1e6, forceInt=False)
        return {"rampNotional":rampNotional,
                "px":SPCFUtils.convertIntexRamp(pxSchedule, term = len(rampNotional), divisor=1, forceInt=False)
                }
            
    @staticmethod
    def copyChangeAssumption(assumptionDict, changeDict):
        copied = SPCFUtils.copyAssumption(assumptionDict)
        copied = SPCFUtils.changeAssumption(copied, changeDict)
        return copied

    @staticmethod
    def copyAssumption(assumptionsDict):
        return assumptionsDict.copy()

    @staticmethod
    def removeAssumption(assumptionsDict, removeList):
        for item in removeList:
            if item in assumptionsDict:
                del assumptionsDict[item]
        return assumptionsDict

    @staticmethod
    def changeAssumption(assumptionsDict, changeDict):
        for k, v in changeDict.items():
            if k in assumptionsDict:
                assumptionsDict[k] = v
        return assumptionsDict
        
    @staticmethod
    def addAssumption(assumptionsDict, addDict):
        for k, v in addDict.items():
            if k not in assumptionsDict:
                assumptionsDict[k] = v
        return assumptionsDict

    @staticmethod
    def convertStrFloat(numStr):
        multiple = 1
        numStr = numStr.replace("$", "")
        numStr = numStr.replace(",", "")
        if "%" in numStr:
            multiple = 0.01
            numStr = numStr.replace("%", "")
        if "mm" in numStr:
            multiple = 1e6
            numStr = numStr.replace("mm", "")

        return float(numStr) * multiple
    
    @staticmethod
    def convertIntexRamp(intexSyntax, term, divisor=1, forceInt=False):
        if isinstance(intexSyntax, (int, float)):
            intexSyntax = str(intexSyntax)

        intexSyntax = intexSyntax.lower()

        if "ramp" in intexSyntax:
            for rampMatch in re.findall(
                r"(\d+\.*\d* +ramp +\d+ +\d+\.*\d*)", intexSyntax
            ):

                rampMatchSplit = rampMatch.split(" ")
                rangeStart = float(rampMatchSplit[0])
                rangeEnd = float(rampMatchSplit[-1])
                rangeTimes = int(rampMatchSplit[-2])

                rampRange = np.linspace(rangeStart, rangeEnd, num=rangeTimes)

                rampList = [f"{item:.2f}" for item in list(rampRange)]

                rampStr = " ".join(rampList)

                intexSyntax = intexSyntax.replace(rampMatch, rampStr, 1)

        if "for" in intexSyntax:
            for forMatch in re.findall(r"(\d+\.*\d* +for +\d+)", intexSyntax):

                forMatchSplit = forMatch.split(" ")
                forList = [forMatchSplit[0]] * int(forMatchSplit[-1])
                forStr = " ".join(forList)
                intexSyntax = intexSyntax.replace(forMatch, forStr, 1)

        intexSyntaxSplit = re.split(r" +", intexSyntax)

        if term is None:
            term = len(intexSyntaxSplit)

        # pad or truncate
        intexSyntaxSplitExtend = intexSyntaxSplit[:term] + [intexSyntaxSplit[-1]] * (
            term - len(intexSyntaxSplit)
        )

        if forceInt:
            res = [int(float(item) / divisor) for item in intexSyntaxSplitExtend]
        else:
            res = [float(item) / divisor for item in intexSyntaxSplitExtend]

        return res

    @staticmethod
    def timingCurveParse(timingInput, term):
        splitTiming = timingInput.split("/")
        splitTimingFloat = [float(item) for item in splitTiming]
        formIntexSyntax = ''
        for item in splitTimingFloat:
            formIntexSyntax = formIntexSyntax + str(item / 12.0) + ' for 12 '
        remainingTiming = 100.0 - sum(splitTimingFloat)
        if remainingTiming < 0.0:
            raise ValueError("timingInput exceeds 100%")

        remainingTimingMonthly = remainingTiming / (term - len(splitTimingFloat) * 12)        
        formIntexSyntax = formIntexSyntax + str(remainingTimingMonthly)
        
        return SPCFUtils.convertIntexRamp(formIntexSyntax, term, divisor=100, forceInt=False)
        
    

    @staticmethod
    def financeFormatNumber(rawNum, formatType):

        if formatType == "pct0":
            res = "{:.0%}".format(rawNum)
        elif formatType == "pct2":
            res = "{:.2%}".format(rawNum)
        elif formatType == "comma":
            res = f"{rawNum:,.0f}"
        elif formatType == "comma2":
            res = f"{rawNum:,.2f}"
        return res

    @staticmethod
    def convertSPRD(x):
        try:
            pctMulti = 1
            if "%" in x:
                x = x.replace("%", "")
                pctIndicator = 100
            if x.strip() == "-":
                return np.nan

            if ("-" in x) and (x.replace(" ", "")[0] != "-"):
                xsplit = x.split("-")
                sprd1 = float(xsplit[0].replace(" ", ""))
                sprd2 = float(xsplit[1].replace(" ", ""))
                return sprd1 + sprd2

            else:
                return float(x) * pctMulti
        except:
            return x

    @staticmethod
    def convertWAL(x):
        if x.strip() == "-":
            return np.nan
        else:
            return float(x)

    @staticmethod
    def findRatingsMinMax(x, findMin=True):
        xadjust = [item for item in x if ((item > 0) and (item < 9999))]
        if len(xadjust) == 0:
            return min(x) if findMin else max(x)
        else:
            return min(xadjust) if findMin else max(xadjust)

    @staticmethod
    def weightAvg(x, y, weightCol, fillna=False):
        if x.empty:
            return None
        else:
            if fillna:
                x = x.fillna(0)
            x = x.dropna()
            if np.sum(y.loc[x.index, weightCol]) == 0:
                return 0
            else:
                return np.average(x, weights=y.loc[x.index, weightCol])