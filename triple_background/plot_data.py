
import numpy
import pandas
import matplotlib.pyplot as plt

def main(args):
    for subscribers in [10, 25, 40]:
        dataset = pandas.read_csv(f"../test/notif_times{subscribers}.csv")
        sizer = dataset["subscriptions"][0]
        print(f"Dataset size is {dataset.shape[0]}")
        print(f"Subscribers are #{sizer}, attemps are {dataset.shape[0]/sizer}")

        npArray = dataset.to_numpy()
        
        offset = 0
        minimals = numpy.array([])
        maximals = numpy.array([])
        indexes = numpy.array([])
        for s in range(int(dataset.shape[0]/sizer)):
            subArray = npArray[s*sizer:(s+1)*sizer,:]
            print(s)
            max_time = numpy.max(subArray, axis=0)[-1]
            print(max_time)
            maximals = numpy.append(maximals,max_time)
            min_time = numpy.min(subArray, axis=0)[-1]
            minimals = numpy.append(minimals,min_time)
            triples = subArray[0,0]
            indexes = numpy.append(indexes,triples)
            #print(f"max for {triples} is {max_time}")
            #print(f"min for {triples} is {min_time}")

        print(indexes)
        plt.subplot(1,2,1)
        plt.plot(indexes,minimals, "s-", label=f"Minimum time @{subscribers} subscribers")
        plt.title("Minimum times")
        plt.legend()
        plt.xlabel("Number of triples in the dataset")
        plt.ylabel("Time [s] to notify")

        plt.subplot(1,2,2)
        plt.plot(indexes,maximals, "s--", label=f"Maximum time @{subscribers} subscribers")
        plt.title("Maximum times")
        plt.legend()
        plt.xlabel("Number of triples in the dataset")
        plt.ylabel("Time [s] to notify")
    plt.show()

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))