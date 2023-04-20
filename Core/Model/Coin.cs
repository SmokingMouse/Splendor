using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace Splendor.Core.Model
{
    public class CoinSet
    {
        private Dictionary<Color, int>? coin_sets;

        public CoinSet() 
        {
            this.coin_sets = new Dictionary<Color, int>();
        }

        public KeyValuePair<Color,int>? Take(Color color, int count) 
        {
            if (this.coin_sets is not Dictionary<Color,int> || this.coin_sets.GetValueOrDefault(color,0) < count)  
            {
                return null;
            } else {
                this.coin_sets[color] -= count;
                return new KeyValuePair<Color, int>(color,count);
            }
        }

        public void Put(KeyValuePair<Color,int> coins) 
        {
            if (this.coin_sets is Dictionary<Color,int>) 
            {
                this.coin_sets.Add(coins.Key,coins.Value);
            }
        }

        public string String() 
        {
            var s = new List<string>();
            if (this.coin_sets is not null) {
                foreach (var i in this.coin_sets) 
                {
                    // Console.WriteLine(i);
                    s.Add(string.Format("<{0},{1}>",i.Key,i.Value));
                }
            }
            return string.Join('\n',s);
        }
    }
}
