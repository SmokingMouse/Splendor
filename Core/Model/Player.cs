using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace Splendor.Core.Model
{

    public class StoreArea
    {
        private List<Card?> store_cards;

        public StoreArea() 
        {
            this.store_cards = new List<Card?>(new Card?[]{null,null,null});
        }

        public int Store(Card c) 
        {
            foreach(int i in Enumerable.Range(0,3))
            {
                if (this.store_cards[i] is null )
                {
                    this.store_cards[i] = c; 
                    return i;
                }
            }
            return -1;
        }

        public Card? Take(int i) 
        {
            var r = this.Get(i);
            this.store_cards[i] = null;
            return r;
        }

        public Card? Get(int i)
        {
            return this.store_cards[i];
        }
    }

    public class Player
    {
        private string? id;
        private StoreArea? store_area;
        private CoinSet? coin_set;
        private CardSet? pursed_cards;

        public Player(string id) 
        {
            this.id = id;
            this.store_area = new StoreArea();
            this.coin_set = new CoinSet();
            this.pursed_cards = new CardSet();
        }
    }
}