import random
t_start = 0 
t_end = 20
new_time = 0

def time_count(start_val):
    current_time = start_val
    new_time = current_time + 1
    current_time = new_time
    print("time at " + str(new_time))
    
def appender(time, data_0, data_1):
     # open logs/data.csv, append
    file = open("logs/power_logs.csv", "a")
    
    # type conversions for appending
    str_csv = ", "
    str_data_0 = str(data_0)
    str_data_1 = str(data_1)
    str_time = str(time)

    file.write(str(time) + str_csv)
    file.write(str_data_0 + str_csv)
    file.write(str_data_1 + str_csv)
    file.write("\n")

    return 0
            
# main program here
for x in range(t_end):
    time_count(t_start)
    #appender(time, 0, 1)