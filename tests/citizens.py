#!/usr/bin/env python3
"""
Generates a large set of valid citizens data.

Useful for testing.
"""
import argparse 

from collections import OrderedDict
import json
from faker import Faker
from faker.providers import BaseProvider


class CitizenProvider(BaseProvider):
    """
    Generates valid citizen profiles according to specification.
    The 'relatives' field left empty and must be set separately.
    """
    building_formats = ('%#','%', '%%к%','%%к%стр%')

    def town(self):
        towns = OrderedDict([
                ("Москва", 0.5),
                ("Санкт-Петербург", 0.2),
                ("Екатеринбург", 0.1),
                ("Новосибирск", 0.1),
                ("Краснодар", 0.1),
                ])
        return self.random_element(towns)

    def citizen(self, id = None, town=None, gender=None, ):
        
        GENDER = ["male", "female",]

        if not gender:
            gender = self.random_element(GENDER)

        if gender == "male":
            name = self.generator.name_male()
        elif gender == "female":
            name = self.generator.name_female()
        else:
            raise ValueError("`gender` not in {}!".format(GENDER))
            
        if not town:
            town = self.town()

        return OrderedDict([
                    ("citizen_id", id ),
                    ("town", town ),
                    ("street", self.generator.street_title()),
                    ("building", self.numerify(
                                    self.random_element(
                                        self.building_formats))),
                    ("apartment", self.random_int(1,399)),
                    ("name", name),
                    ("birth_date", self.generator.date_of_birth().strftime("%d.%m.%Y")),
                    ("gender", gender), 
                    ("relatives", []),
                    ])


def rand_pairs(n, k):
    """
    Return generator for k random paris with replacement for n items:
    items could be paired with itself.
    
    WARNING: It's O(k**2), so don't set k too high!
    """
    from itertools import combinations_with_replacement
    from random import sample

    subset = sample(range(n), min(n, k*2))  # useful if k << n
    n_combinations = (len(subset)+1) * len(subset) // 2  # sum(1...n) = (n+1)*n/2
  
    if k > n_combinations:
        raise ValueError('requested number of pairs is more than maximum possible')
  
    selection = list(sample(range(n_combinations), k))  #random combination indices
    gen = combinations_with_replacement(subset, 2)

    sel = iter(sorted(selection))
    n = next(sel)

    for i, x in enumerate(gen):
        if i == n:
            yield(x)
            n = next(sel)


def add_k_random_relatives(citizens, k, sort=True):
    """
        Modify citizens, add k random relatives.
        The citizen could be relative to itself.
    """
    pairs = rand_pairs(len(citizens), k)

    changed = set()

    for a,b in pairs:
        id_a = citizens[a]['citizen_id']
        id_b = citizens[b]['citizen_id']

        rel_a = citizens[a]['relatives']
        rel_b = citizens[b]['relatives']

        if id_b not in rel_a:
            rel_a.append(id_b)
        if id_a not in rel_b:
            rel_b.append(id_a) 

        if sort:
            changed.update((a,b))

    if sort:
        for i in changed:
            citizens[i]['relatives'].sort()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-n', '--number', metavar='N', type=int,
                        help='number of citizens')
    parser.add_argument('-k', '--links', metavar='K', type=int,
                        help='number of relatives')
    args = parser.parse_args()
                
    fake = Faker('ru_RU')
    fake.add_provider(CitizenProvider)
    fake.seed(12345)  # Make it reproducible

    N = args.number or 3
    K = args.links or 3

    citizens = [ fake.citizen(i) for i in range(1,N+1)]
    add_k_random_relatives(citizens, K, sort=True)
    
    ret = json.dumps({"citizens": citizens},
            ensure_ascii=False, indent=2)

    print(ret)


if __name__ == "__main__":
    main()
