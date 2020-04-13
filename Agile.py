import requests
from datetime import datetime, timedelta, date
import collections


class Agile:
    area_code = None

    def __init__(self, area_code):
        self.area_code = area_code

    def get_min_times(self, num, in_d, requirements):
        ret_d = {}
        d = {}
        d.update(in_d)
        for i in range(num):
            min_key = min(d, key=d.get)
            ret_d[min_key] = d[min_key]
            del d[min_key]
        for requirement in requirements:
            slots_filled = []
            after_time = datetime.strptime(requirement["time_from"], "%Y-%m-%dT%H:%M:%SZ")
            before_time = datetime.strptime(requirement["time_to"], "%Y-%m-%dT%H:%M:%SZ")
            min_slots = requirement["slots"]

            for time, rate in ret_d.items():
                dttime = datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
                if after_time < dttime < before_time:
                    slots_filled.append(time)
            if len(slots_filled) < min_slots:
                for slot in slots_filled:
                    del (ret_d[slot])
                new_rates = self.get_rates(requirement["time_from"], requirement["time_to"])
                new_mins = self.get_min_times(min_slots, new_rates["date_rates"], [])
                remove_list = self.get_max_times(min_slots - len(slots_filled), ret_d)
                for time, rate in remove_list.items():
                    del (ret_d[time])
                for time, rate in new_mins.items():
                    ret_d[time] = rate
        return ret_d

    def get_max_times(self, num, in_d):
        ret_d = {}
        d = {}
        d.update(in_d)
        for i in range(num):
            min_key = max(d, key=d.get)
            ret_d[min_key] = d[min_key]
            del d[min_key]
        return ret_d


    def get_min_time_run(self, hours, in_d):
        slots = hours*2
        d = {}
        d.update(collections.OrderedDict(reversed(list(in_d.items()))))  # Dict was in wrong order
        keys = list(d.keys())
        avgs = {}
        for index, obj in enumerate(keys):
            this_avg = []
            for offset in range(0,slots):
                if index+offset < len(keys):
                    this_avg.append(d[keys[index+offset]])
                else:
                    min_key = min(avgs, key=avgs.get)
                    return {min_key: avgs[min_key]}
            # print(keys[index], this_avg, sum(this_avg)/slots)
            avgs[keys[index]] = sum(this_avg)/slots


    def get_rates_delta(self, day_delta):
        # headers = {'content-type': 'application/json'}
        minute = 00
        if datetime.now().minute > 30:
            minute = 30
        prev_day = date.today() - timedelta(days=day_delta)
        this_day = date.today() - timedelta(days=day_delta-1)

        # print(prev_day.strftime('%Y-%m-%d'), this_day.strftime('%Y-%m-%d'))

        # date_from = f"?period_from={ datetime.now().year }-{ datetime.now().month }-" \
        #             f"{ datetime.now().day }T{ datetime.now().hour }:{ minute }"
        date_from = f"{ prev_day.strftime('%Y-%m-%d') }T00:00"
        date_to = f"{ this_day.strftime('%Y-%m-%d') }T00:00"
        # print(date_from)
        return self.get_rates(date_from, date_to)

    def get_rates(self, date_from, date_to):
        date_from = f"?period_from={ date_from }"
        date_to = f"&period_to={ date_to }"
        headers = {'content-type': 'application/json'}
        r = requests.get(f'https://api.octopus.energy/v1/products/AGILE-18-02-21/electricity-tariffs/'
                         f'E-1R-AGILE-18-02-21-{self.area_code}/'
                         f'standard-unit-rates/{ date_from }{ date_to }', headers=headers)
        # print(json.dumps(r.json(), indent=4))
        # print(r.content)
        # print(r.url)
        results = r.json()["results"]

        date_rates = collections.OrderedDict()

        rate_list = []
        low_rate_list = []

        for result in results:
            price = result["value_inc_vat"]
            valid_from = result["valid_from"]
            valid_to = result["valid_to"]
            date_rates[valid_from] = price
            # print(valid_from)
            rate_list.append(price)
            if price < 15:
                low_rate_list.append(price)

        return {"date_rates": date_rates, "rate_list": rate_list, "low_rate_list": low_rate_list}

    def summary(self):
        all_rates = {}
        all_rates_list = []
        all_low_rates_list = []
        water_rates = []
        days=0
        for i in range(0, 1):
            rates = self.get_rates_delta(i)
            rate_list = rates["rate_list"]
            low_rate_list = rates["low_rate_list"]
            date_rates = rates["date_rates"]
            all_rates.update(date_rates)
            all_rates_list.extend(rate_list)
            all_low_rates_list.extend(low_rate_list)

            mean_price = sum(rate_list)/len(rate_list)
            low_mean_price = sum(low_rate_list)/len(low_rate_list)

            cheapest6 = self.get_min_times(6, date_rates)
            # day = datetime.fromisoformat(next(iter(date_rates)))
            day = datetime.strptime(next(iter(date_rates)), '%Y-%m-%dT%H:%M:%SZ').strftime("%Y-%m-%d")

            minTimeHrs = self.get_min_time_run(4, date_rates)
            minTimeHrsTime = list(minTimeHrs.keys())[0]
            minTimeHrsRate = minTimeHrs[list(minTimeHrs.keys())[0]]
            water_rates.append(minTimeHrsRate)

            # print(f"({day})                {cheapest6}")
            # print(f"({day}) Avg Price:     {mean_price}")
            # print(f"({day}) Low Avg Price: {low_mean_price}")
            # print(f"({day}) Min Price:     {min(rate_list)}")
            # print(f"({day}) Max Price:     {max(rate_list)}")
            # print(f"({day}) Min 4 Hr Run:  {minTimeHrsTime}: {minTimeHrsRate}")
            days+=1
            print(".", end="")
            if days%50 == 0:
                print()
        print()


        # # print(f"({day}) Avg Price: {mean_price}")
        overall_min = min(all_rates, key=all_rates.get)
        overall_max = max(all_rates, key=all_rates.get)

        mean_price = sum(all_rates_list) / len(all_rates_list)
        low_mean_price = sum(all_low_rates_list) / len(all_low_rates_list)
        avg_water_price = sum(water_rates)/len(water_rates)
        avg_water_usage = 7.738
        print()
        print("Overall stats:")
        print(f"Avg Price:       {mean_price}")
        print(f"Low Avg Price:   {low_mean_price}")
        print(f"Avg Water Price: {avg_water_price} (£{round(avg_water_usage*(avg_water_price/100), 2)}/day), "
              f"(£{round(avg_water_usage*(avg_water_price/100)*365, 2)}/year)")
        print(f"Cur Water Price: {avg_water_price} (£{round(avg_water_usage*(15.44/100), 2)}/day), "
              f"(£{round(avg_water_usage*(15.44/100)*365, 2)}/year)")
        print(f"Min Price:       {overall_min}: {all_rates[overall_min]}")
        print(f"Max Price:       {overall_max}: {all_rates[overall_max]}")
        print(f"Num Days:        {days}")

        # print(all_rates)